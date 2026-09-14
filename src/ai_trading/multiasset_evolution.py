from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from .evolution_manager import run_evolution_cycle
from .expert_diversity import DiversityReport, evaluate_expert_diversity
from .expert_pool import ExpertPoolStore, ExpertRecord
from .expert_returns import equal_weight_pool_returns, specialist_return_series
from .generation_rollback import rollback_generation
from .generations import GenerationStore
from .global_selection import evaluate_global_generation
from .performance import compute_metrics


@dataclass(frozen=True)
class MultiAssetEvolutionResult:
    symbols: tuple[str, ...]
    evolved_symbols: int
    generation: int
    portfolio_score: float
    diversified: bool
    max_pair_correlation: float
    rolled_back: bool
    accepted: bool
    reason: str


def _symbol_pool_returns(
    df: pd.DataFrame,
    *,
    symbol: str,
    records: dict[str, ExpertRecord],
) -> pd.Series | None:
    series: dict[str, pd.Series] = {}
    for record in records.values():
        if record.status != "active" or not record.name.startswith(f"{symbol}:"):
            continue
        parts = record.name.split(":")
        threshold_part = next((p for p in parts if p.startswith("t")), None)
        if threshold_part is None:
            continue
        try:
            threshold = float(threshold_part[1:])
        except ValueError:
            continue
        try:
            series[record.name] = specialist_return_series(
                df,
                kind=record.kind,
                return_threshold=threshold,
            )
        except ValueError:
            continue

    if not series:
        return None
    try:
        return equal_weight_pool_returns(series)
    except ValueError:
        return None


def _global_portfolio_returns(
    markets: dict[str, pd.DataFrame],
    records: dict[str, ExpertRecord],
) -> tuple[pd.Series | None, pd.DataFrame]:
    per_symbol: dict[str, pd.Series] = {}
    for symbol, df in markets.items():
        returns = _symbol_pool_returns(df, symbol=symbol, records=records)
        if returns is not None:
            per_symbol[symbol] = returns

    if not per_symbol:
        return None, pd.DataFrame()

    frame = pd.DataFrame(per_symbol).dropna()
    if len(frame) < 20:
        return None, frame
    return frame.mean(axis=1), frame


def _score(returns: pd.Series | None) -> float:
    if returns is None or len(returns) < 2:
        return 0.0
    equity = (1.0 + returns).cumprod() * 100_000.0
    return float(compute_metrics(equity).sharpe)


def _diversity(
    frame: pd.DataFrame,
    max_pair_correlation: float,
) -> DiversityReport:
    if frame.empty:
        return DiversityReport(0.0, 0.0, True)
    return evaluate_expert_diversity(
        frame,
        max_pair_correlation=max_pair_correlation,
    )


def run_multiasset_evolution_cycle(
    markets: dict[str, pd.DataFrame],
    *,
    pool: ExpertPoolStore | None = None,
    generations: GenerationStore | None = None,
    parent_limit: int = 2,
    max_pair_correlation: float = 0.85,
) -> MultiAssetEvolutionResult:
    if len(markets) < 2:
        raise ValueError("Need at least two assets")

    pool = pool or ExpertPoolStore()
    generations = generations or GenerationStore(
        "artifacts/global_expert_lineage.json",
        "artifacts/global_generations.jsonl",
    )

    symbols = tuple(sorted(markets))
    baseline_records = pool.load()
    baseline_returns, _baseline_frame = _global_portfolio_returns(markets, baseline_records)
    baseline_score = _score(baseline_returns)

    baseline_active = [
        name
        for name, record in baseline_records.items()
        if record.status == "active"
    ]
    generations.snapshot(baseline_active, baseline_score)

    evolved = 0
    local_rollback = False
    for symbol in symbols:
        result = run_evolution_cycle(
            markets[symbol],
            symbol=symbol,
            store=pool,
            generation_store=generations,
            parent_limit=parent_limit,
        )
        if result.accepted > 0 or result.replaced > 0:
            evolved += 1
        local_rollback = local_rollback or result.rolled_back

    candidate_records = pool.load()
    candidate_returns, candidate_frame = _global_portfolio_returns(
        markets,
        candidate_records,
    )
    candidate_score = _score(candidate_returns)
    diversity = _diversity(candidate_frame, max_pair_correlation)

    decision = evaluate_global_generation(
        previous_score=baseline_score,
        current_score=candidate_score,
        diversity=diversity,
    )

    rolled_back = local_rollback
    if not decision.accept:
        rollback_generation(pool, generations)
        rolled_back = True

    final_records = pool.load()
    final_returns, final_frame = _global_portfolio_returns(markets, final_records)
    final_score = _score(final_returns)
    final_diversity = _diversity(final_frame, max_pair_correlation)
    final_active = [
        name
        for name, record in final_records.items()
        if record.status == "active"
    ]
    final_snapshot = generations.snapshot(final_active, final_score)

    return MultiAssetEvolutionResult(
        symbols=symbols,
        evolved_symbols=evolved,
        generation=final_snapshot.generation,
        portfolio_score=final_score,
        diversified=final_diversity.diversified,
        max_pair_correlation=final_diversity.max_pair_correlation,
        rolled_back=rolled_back,
        accepted=decision.accept and not rolled_back,
        reason=decision.reason,
    )

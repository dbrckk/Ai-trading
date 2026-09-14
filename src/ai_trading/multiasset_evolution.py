from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from .evolution_manager import run_evolution_cycle
from .expert_diversity import evaluate_expert_diversity
from .expert_pool import ExpertPoolStore
from .expert_returns import equal_weight_pool_returns, specialist_return_series
from .generations import GenerationStore
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


def _symbol_pool_returns(
    df: pd.DataFrame,
    *,
    symbol: str,
    records,
) -> pd.Series | None:
    series: dict[str, pd.Series] = {}
    for record in records.values():
        if record.status != "active" or not record.name.startswith(f"{symbol}:"):
            continue
        parts = record.name.split(":")
        horizon_part = next((p for p in parts if p.startswith("h") and p[1:].isdigit()), None)
        threshold_part = next((p for p in parts if p.startswith("t")), None)
        if horizon_part is None or threshold_part is None:
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
    records,
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
    evolved = 0
    rolled_back = False

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
        rolled_back = rolled_back or result.rolled_back

    records = pool.load()
    global_returns, per_symbol = _global_portfolio_returns(markets, records)
    diversity = evaluate_expert_diversity(
        per_symbol,
        max_pair_correlation=max_pair_correlation,
    ) if not per_symbol.empty else None

    portfolio_score = 0.0
    if global_returns is not None and len(global_returns) >= 2:
        equity = (1.0 + global_returns).cumprod() * 100_000.0
        portfolio_score = float(compute_metrics(equity).sharpe)

    active_names = [
        name
        for name, record in records.items()
        if record.status == "active"
    ]
    snapshot = generations.snapshot(active_names, portfolio_score)

    return MultiAssetEvolutionResult(
        symbols=symbols,
        evolved_symbols=evolved,
        generation=snapshot.generation,
        portfolio_score=portfolio_score,
        diversified=True if diversity is None else diversity.diversified,
        max_pair_correlation=0.0 if diversity is None else diversity.max_pair_correlation,
        rolled_back=rolled_back,
    )

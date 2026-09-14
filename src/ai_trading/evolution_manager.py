from __future__ import annotations

import re
from dataclasses import dataclass

import pandas as pd

from .crisis_gate import promotions_allowed
from .evolution import MutationConfig, mutate_expert, top_parents
from .expert_factory import ExpertCandidate
from .expert_pool import ExpertPoolStore, ExpertRecord, reconcile_pool
from .expert_returns import equal_weight_pool_returns, specialist_return_series
from .generation_progress import compare_generations
from .generation_rollback import rollback_generation
from .generations import GenerationStore
from .marginal_alpha import evaluate_marginal_alpha
from .performance import compute_metrics
from .portfolio_selection import evaluate_portfolio_replacement
from .temporal_cv import TemporalCVReport, temporal_cross_validate_specialist


@dataclass(frozen=True)
class EvolutionCycleResult:
    evaluated: int
    accepted: int
    replaced: int
    generation: int
    rolled_back: bool
    mutated: tuple[ExpertCandidate, ...]


def _record_to_candidate(record: ExpertRecord) -> ExpertCandidate | None:
    match = re.search(r":h(?P<horizon>\d+):t(?P<threshold>[^:]+)", record.name)
    if match is None:
        return None
    try:
        horizon = int(match.group("horizon"))
        threshold = float(match.group("threshold"))
    except ValueError:
        return None
    return ExpertCandidate(
        name=record.name,
        kind=record.kind,
        horizon_bars=horizon,
        return_threshold=threshold,
        compute_cost=record.compute_cost,
    )


def _active_pool_returns(
    df: pd.DataFrame,
    records: dict[str, ExpertRecord],
    symbol: str,
) -> pd.Series | None:
    series: dict[str, pd.Series] = {}
    for record in records.values():
        if record.status != "active" or not record.name.startswith(f"{symbol}:"):
            continue
        candidate = _record_to_candidate(record)
        if candidate is None:
            continue
        try:
            series[record.name] = specialist_return_series(
                df,
                kind=candidate.kind,
                return_threshold=candidate.return_threshold,
                horizon_bars=candidate.horizon_bars,
            )
        except ValueError:
            continue
    if not series:
        return None
    try:
        return equal_weight_pool_returns(series)
    except ValueError:
        return None


def _portfolio_score(returns: pd.Series | None) -> float:
    if returns is None or len(returns) < 2:
        return 0.0
    equity = (1.0 + returns).cumprod() * 100_000.0
    return float(compute_metrics(equity).sharpe)


def run_evolution_cycle(
    df: pd.DataFrame,
    *,
    symbol: str,
    store: ExpertPoolStore | None = None,
    generation_store: GenerationStore | None = None,
    mutation_config: MutationConfig | None = None,
    parent_limit: int = 3,
) -> EvolutionCycleResult:
    store = store or ExpertPoolStore()
    generation_store = generation_store or GenerationStore()
    records = store.load()
    if not promotions_allowed():
        return EvolutionCycleResult(
            evaluated=0,
            accepted=0,
            replaced=0,
            generation=generation_store.current_generation(),
            rolled_back=False,
            mutated=(),
        )

    parents = top_parents(records, symbol=symbol, limit=parent_limit)
    baseline_returns = _active_pool_returns(df, records, symbol)

    mutations: list[ExpertCandidate] = []
    parent_by_child: dict[str, str] = {}
    for parent_record in parents:
        parent = _record_to_candidate(parent_record)
        if parent is None:
            continue
        children = mutate_expert(
            parent,
            symbol=symbol,
            config=mutation_config,
        )
        mutations.extend(children)
        for child in children:
            parent_by_child[child.name] = parent_record.name

    accepted = 0
    replaced = 0
    next_generation = generation_store.current_generation() + 1

    for candidate in mutations:
        try:
            report: TemporalCVReport = temporal_cross_validate_specialist(
                df,
                kind=candidate.kind,
                return_threshold=candidate.return_threshold,
                horizon_bars=candidate.horizon_bars,
            )
            candidate_returns = specialist_return_series(
                df,
                kind=candidate.kind,
                return_threshold=candidate.return_threshold,
                horizon_bars=candidate.horizon_bars,
            )
        except ValueError:
            continue

        if report.aggregate_score < 0.55:
            continue

        portfolio_approved = baseline_returns is None
        if baseline_returns is not None:
            try:
                marginal = evaluate_marginal_alpha(
                    baseline_returns,
                    candidate_returns,
                )
            except ValueError:
                continue

            active_scores = [
                r.score
                for r in records.values()
                if r.status == "active" and r.name.startswith(f"{symbol}:")
            ]
            incumbent_score = min(active_scores) if active_scores else 0.0
            replacement = evaluate_portfolio_replacement(
                marginal,
                incumbent_score=incumbent_score,
                challenger_score=report.aggregate_score,
            )
            portfolio_approved = replacement.replace

        if not portfolio_approved:
            continue

        existing = records.get(candidate.name)
        records[candidate.name] = ExpertRecord(
            name=candidate.name,
            kind=candidate.kind,
            status=existing.status if existing else "challenger",
            score=float(report.aggregate_score),
            economic_score=existing.economic_score if existing else 0.0,
            validation_score=float(report.aggregate_score),
            observations=sum(f.observations for f in report.folds),
            compute_cost=float(candidate.compute_cost),
        )
        generation_store.add_lineage(
            candidate.name,
            parent_by_child.get(candidate.name),
            next_generation,
        )
        accepted += 1
        if baseline_returns is not None:
            replaced += 1

    reconciled = reconcile_pool(records)
    store.save(reconciled)

    new_returns = _active_pool_returns(df, reconciled, symbol)
    active_names = [
        name
        for name, record in reconciled.items()
        if record.status == "active" and name.startswith(f"{symbol}:")
    ]
    snapshot = generation_store.snapshot(
        active_names,
        _portfolio_score(new_returns),
    )

    rolled_back = False
    snapshots = generation_store.snapshots()
    if len(snapshots) >= 2:
        progress = compare_generations(snapshots[-2], snapshots[-1])
        if not progress.improved:
            rollback_generation(store, generation_store)
            rolled_back = True

    return EvolutionCycleResult(
        evaluated=len(mutations),
        accepted=accepted,
        replaced=replaced,
        generation=snapshot.generation,
        rolled_back=rolled_back,
        mutated=tuple(mutations),
    )

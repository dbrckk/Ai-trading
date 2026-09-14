from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from .evolution import MutationConfig, mutate_expert, top_parents
from .expert_factory import ExpertCandidate
from .expert_pool import ExpertPoolStore, ExpertRecord, reconcile_pool
from .temporal_cv import TemporalCVReport, temporal_cross_validate_specialist


@dataclass(frozen=True)
class EvolutionCycleResult:
    evaluated: int
    accepted: int
    mutated: tuple[ExpertCandidate, ...]


def _record_to_candidate(record: ExpertRecord) -> ExpertCandidate | None:
    parts = record.name.split(":")
    if len(parts) < 4:
        return None
    try:
        horizon = int(parts[-2].lstrip("h"))
        threshold = float(parts[-1].removesuffix(":mut").lstrip("t"))
    except ValueError:
        return None
    return ExpertCandidate(
        name=record.name,
        kind=record.kind,
        horizon_bars=horizon,
        return_threshold=threshold,
        compute_cost=record.compute_cost,
    )


def run_evolution_cycle(
    df: pd.DataFrame,
    *,
    symbol: str,
    store: ExpertPoolStore | None = None,
    mutation_config: MutationConfig | None = None,
    parent_limit: int = 3,
) -> EvolutionCycleResult:
    store = store or ExpertPoolStore()
    records = store.load()
    parents = top_parents(records, symbol=symbol, limit=parent_limit)

    mutations: list[ExpertCandidate] = []
    for parent_record in parents:
        parent = _record_to_candidate(parent_record)
        if parent is None:
            continue
        mutations.extend(
            mutate_expert(
                parent,
                symbol=symbol,
                config=mutation_config,
            )
        )

    accepted = 0
    for candidate in mutations:
        try:
            report: TemporalCVReport = temporal_cross_validate_specialist(
                df,
                kind=candidate.kind,
                return_threshold=candidate.return_threshold,
            )
        except ValueError:
            continue

        if report.aggregate_score < 0.55:
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
        accepted += 1

    reconciled = reconcile_pool(records)
    store.save(reconciled)

    return EvolutionCycleResult(
        evaluated=len(mutations),
        accepted=accepted,
        mutated=tuple(mutations),
    )

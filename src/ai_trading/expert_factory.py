from __future__ import annotations

from dataclasses import dataclass
from itertools import product

import pandas as pd

from .expert_pool import ExpertPoolStore, ExpertRecord, reconcile_pool
from .expert_sandbox import validate_specialist


@dataclass(frozen=True)
class ExpertCandidate:
    name: str
    kind: str
    horizon_bars: int
    return_threshold: float
    compute_cost: float


@dataclass(frozen=True)
class FactoryConfig:
    horizons: tuple[int, ...] = (1, 3, 5)
    return_thresholds: tuple[float, ...] = (0.0005, 0.001, 0.002)
    kinds: tuple[str, ...] = ("trend", "range", "high_vol")
    max_candidates: int = 12
    max_promotions_per_run: int = 3


@dataclass(frozen=True)
class FactoryResult:
    evaluated: int
    promoted: int
    candidates: tuple[ExpertCandidate, ...]


def generate_candidates(
    symbol: str,
    config: FactoryConfig | None = None,
) -> list[ExpertCandidate]:
    config = config or FactoryConfig()
    candidates: list[ExpertCandidate] = []

    cost_by_kind = {
        "trend": 0.8,
        "range": 1.5,
        "high_vol": 1.2,
    }

    for kind, horizon, threshold in product(
        config.kinds,
        config.horizons,
        config.return_thresholds,
    ):
        name = f"{symbol}:{kind}:h{horizon}:t{threshold:g}"
        candidates.append(
            ExpertCandidate(
                name=name,
                kind=kind,
                horizon_bars=horizon,
                return_threshold=threshold,
                compute_cost=cost_by_kind[kind] * max(1.0, horizon / 3.0),
            )
        )

    return candidates[: config.max_candidates]


def run_expert_factory(
    df: pd.DataFrame,
    *,
    symbol: str,
    store: ExpertPoolStore | None = None,
    config: FactoryConfig | None = None,
) -> FactoryResult:
    store = store or ExpertPoolStore()
    config = config or FactoryConfig()
    records = store.load()

    evaluated: list[ExpertCandidate] = []
    before_active = {
        name for name, record in records.items() if record.status == "active"
    }

    for candidate in generate_candidates(symbol, config):
        try:
            result = validate_specialist(
                df,
                kind=candidate.kind,
                return_threshold=candidate.return_threshold,
            )
        except ValueError:
            continue

        existing = records.get(candidate.name)
        economic_score = existing.economic_score if existing else 0.0
        combined = (
            0.70 * result.validation_score
            + 0.30 * max(0.0, min(1.0, 0.5 + economic_score))
        )

        records[candidate.name] = ExpertRecord(
            name=candidate.name,
            kind=candidate.kind,
            status=existing.status if existing else "challenger",
            score=float(combined),
            economic_score=float(economic_score),
            validation_score=float(result.validation_score),
            observations=result.observations,
            compute_cost=float(candidate.compute_cost),
        )
        evaluated.append(candidate)

    reconciled = reconcile_pool(records)

    newly_active = [
        name
        for name, record in reconciled.items()
        if record.status == "active" and name not in before_active
    ]

    if len(newly_active) > config.max_promotions_per_run:
        keep = set(
            sorted(
                newly_active,
                key=lambda n: reconciled[n].score,
                reverse=True,
            )[: config.max_promotions_per_run]
        )
        reconciled = {
            name: (
                record
                if name not in newly_active or name in keep
                else ExpertRecord(
                    name=record.name,
                    kind=record.kind,
                    status="challenger",
                    score=record.score,
                    economic_score=record.economic_score,
                    validation_score=record.validation_score,
                    observations=record.observations,
                    compute_cost=record.compute_cost,
                )
            )
            for name, record in reconciled.items()
        }

    store.save(reconciled)
    promoted = sum(
        1
        for name, record in reconciled.items()
        if record.status == "active" and name not in before_active
    )

    return FactoryResult(
        evaluated=len(evaluated),
        promoted=promoted,
        candidates=tuple(evaluated),
    )

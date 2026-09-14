from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from .crisis_gate import promotions_allowed
from .expert_pool import (
    ExpertPoolPolicy,
    ExpertPoolStore,
    ExpertRecord,
    reconcile_pool,
)
from .expert_sandbox import SandboxResult, validate_specialist


@dataclass(frozen=True)
class PoolRefreshResult:
    records: dict[str, ExpertRecord]
    sandbox: dict[str, SandboxResult]


def refresh_expert_pool(
    df: pd.DataFrame,
    *,
    symbol: str,
    store: ExpertPoolStore | None = None,
    policy: ExpertPoolPolicy | None = None,
) -> PoolRefreshResult:
    store = store or ExpertPoolStore()
    policy = policy or ExpertPoolPolicy()

    sandbox_results: dict[str, SandboxResult] = {}
    records = store.load()

    compute_costs = {
        "trend": 0.8,
        "range": 1.5,
        "high_vol": 1.2,
    }

    for kind in ("trend", "range", "high_vol"):
        result = validate_specialist(df, kind=kind)
        sandbox_results[kind] = result
        name = f"{symbol}:{kind}"

        previous = records.get(name)
        economic_score = previous.economic_score if previous is not None else 0.0
        observations = (
            max(previous.observations, result.observations)
            if previous is not None
            else result.observations
        )
        combined = (
            0.70 * result.validation_score
            + 0.30 * max(0.0, min(1.0, 0.5 + economic_score))
        )

        records[name] = ExpertRecord(
            name=name,
            kind=kind,
            status=previous.status if previous is not None else "challenger",
            score=float(combined),
            economic_score=float(economic_score),
            validation_score=float(result.validation_score),
            observations=observations,
            compute_cost=compute_costs[kind],
        )

    reconciled = reconcile_pool(records, policy)
    if not promotions_allowed():
        reconciled = {
            name: (
                ExpertRecord(
                    name=record.name,
                    kind=record.kind,
                    status="challenger",
                    score=record.score,
                    economic_score=record.economic_score,
                    validation_score=record.validation_score,
                    observations=record.observations,
                    compute_cost=record.compute_cost,
                )
                if records.get(name) is not None
                and records[name].status != "active"
                and record.status == "active"
                else record
            )
            for name, record in reconciled.items()
        }
    store.save(reconciled)
    return PoolRefreshResult(records=reconciled, sandbox=sandbox_results)

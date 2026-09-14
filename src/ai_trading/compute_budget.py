from __future__ import annotations

from dataclasses import dataclass

from .expert_pool import ExpertRecord


@dataclass(frozen=True)
class ComputeBudget:
    total_units: float = 100.0
    exploration_fraction: float = 0.10


def allocate_compute_budget(
    records: dict[str, ExpertRecord],
    budget: ComputeBudget | None = None,
) -> dict[str, float]:
    budget = budget or ComputeBudget()
    active = {
        name: record
        for name, record in records.items()
        if record.status == "active"
    }
    if not active:
        return {}

    exploration = budget.total_units * budget.exploration_fraction
    exploitation = budget.total_units - exploration

    raw = {
        name: max(0.01, record.score) / max(0.1, record.compute_cost)
        for name, record in active.items()
    }
    total = sum(raw.values())

    base_explore = exploration / len(active)
    return {
        name: base_explore + exploitation * (value / total)
        for name, value in raw.items()
    }

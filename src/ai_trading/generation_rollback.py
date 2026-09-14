from __future__ import annotations

from dataclasses import dataclass

from .expert_pool import ExpertPoolStore, ExpertRecord
from .generations import GenerationSnapshot, GenerationStore


@dataclass(frozen=True)
class GenerationRollbackResult:
    restored: GenerationSnapshot
    active_experts: tuple[str, ...]


def rollback_generation(
    pool: ExpertPoolStore,
    generations: GenerationStore,
) -> GenerationRollbackResult:
    previous = generations.previous()
    records = pool.load()
    restored_names = set(previous.active_experts)

    updated: dict[str, ExpertRecord] = {}
    for name, record in records.items():
        status = "active" if name in restored_names else (
            "challenger" if record.status == "active" else record.status
        )
        updated[name] = ExpertRecord(
            name=record.name,
            kind=record.kind,
            status=status,
            score=record.score,
            economic_score=record.economic_score,
            validation_score=record.validation_score,
            observations=record.observations,
            compute_cost=record.compute_cost,
        )

    pool.save(updated)
    return GenerationRollbackResult(
        restored=previous,
        active_experts=previous.active_experts,
    )

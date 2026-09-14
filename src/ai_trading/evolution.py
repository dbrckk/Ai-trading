from __future__ import annotations

from dataclasses import dataclass
from itertools import islice

from .expert_factory import ExpertCandidate
from .expert_pool import ExpertRecord


@dataclass(frozen=True)
class MutationConfig:
    horizon_steps: tuple[int, ...] = (-2, -1, 1, 2)
    threshold_multipliers: tuple[float, ...] = (0.5, 0.75, 1.25, 1.5)
    max_mutations_per_parent: int = 4


def mutate_expert(
    parent: ExpertCandidate,
    *,
    symbol: str,
    config: MutationConfig | None = None,
) -> list[ExpertCandidate]:
    config = config or MutationConfig()
    mutations: list[ExpertCandidate] = []

    for step in config.horizon_steps:
        horizon = max(1, parent.horizon_bars + step)
        mutations.append(
            ExpertCandidate(
                name=f"{symbol}:{parent.kind}:h{horizon}:t{parent.return_threshold:g}:mut",
                kind=parent.kind,
                horizon_bars=horizon,
                return_threshold=parent.return_threshold,
                compute_cost=parent.compute_cost * (1.0 + 0.05 * abs(step)),
            )
        )

    for mult in config.threshold_multipliers:
        threshold = max(1e-5, parent.return_threshold * mult)
        mutations.append(
            ExpertCandidate(
                name=f"{symbol}:{parent.kind}:h{parent.horizon_bars}:t{threshold:g}:mut",
                kind=parent.kind,
                horizon_bars=parent.horizon_bars,
                return_threshold=threshold,
                compute_cost=parent.compute_cost,
            )
        )

    dedup: dict[str, ExpertCandidate] = {m.name: m for m in mutations}
    return list(islice(dedup.values(), config.max_mutations_per_parent))


def top_parents(
    records: dict[str, ExpertRecord],
    *,
    symbol: str,
    limit: int = 3,
) -> list[ExpertRecord]:
    eligible = [
        r
        for r in records.values()
        if r.name.startswith(f"{symbol}:") and r.status in {"active", "challenger"}
    ]
    eligible.sort(
        key=lambda r: (r.score, r.validation_score, r.economic_score),
        reverse=True,
    )
    return eligible[:limit]

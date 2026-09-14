from __future__ import annotations

from dataclasses import dataclass

from .economic_meta import EconomicMetaStats


@dataclass(frozen=True)
class ExpertLifecyclePolicy:
    min_observations: int = 20
    retire_below_score: float = -0.02
    retrain_below_score: float = -0.005


@dataclass(frozen=True)
class ExpertLifecycleDecision:
    action: str
    reason: str


def evaluate_expert_lifecycle(
    stats: EconomicMetaStats,
    policy: ExpertLifecyclePolicy | None = None,
) -> ExpertLifecycleDecision:
    policy = policy or ExpertLifecyclePolicy()

    if stats.observations < policy.min_observations:
        return ExpertLifecycleDecision("keep", "insufficient observations for lifecycle action")
    if stats.score <= policy.retire_below_score:
        return ExpertLifecycleDecision("retire", "persistent negative economic edge")
    if stats.score <= policy.retrain_below_score:
        return ExpertLifecycleDecision("retrain", "economic edge degraded")
    return ExpertLifecycleDecision("keep", "economic edge acceptable")

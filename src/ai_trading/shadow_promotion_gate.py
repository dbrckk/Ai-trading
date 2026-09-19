from __future__ import annotations

from dataclasses import dataclass

from .shadow_quality import ShadowQualityComparison


@dataclass(frozen=True)
class ShadowPromotionPolicy:
    min_observations: int = 250
    min_score_delta: float = 0.02
    min_accuracy_delta: float = 0.0
    max_brier_increase: float = 0.02
    min_directional_edge_delta: float = 0.0


@dataclass(frozen=True)
class ShadowPromotionGate:
    eligible_for_review: bool
    reasons: tuple[str, ...]
    observations: int
    score_delta: float
    accuracy_delta: float
    brier_delta: float
    directional_edge_delta: float


def evaluate_shadow_promotion_gate(
    comparison: ShadowQualityComparison,
    policy: ShadowPromotionPolicy | None = None,
) -> ShadowPromotionGate:
    policy = policy or ShadowPromotionPolicy()
    reasons: list[str] = []

    score_delta = float(comparison.challenger.score - comparison.river.score)
    accuracy_delta = float(
        comparison.challenger.accuracy - comparison.river.accuracy
    )
    brier_delta = float(comparison.challenger.brier - comparison.river.brier)
    directional_edge_delta = float(
        comparison.challenger.directional_edge
        - comparison.river.directional_edge
    )

    if comparison.observations < policy.min_observations:
        reasons.append(
            f"need at least {policy.min_observations} realized shadow observations"
        )
    if score_delta < policy.min_score_delta:
        reasons.append("composite quality improvement below threshold")
    if accuracy_delta < policy.min_accuracy_delta:
        reasons.append("accuracy degraded versus River")
    if brier_delta > policy.max_brier_increase:
        reasons.append("calibration error degraded beyond tolerance")
    if directional_edge_delta < policy.min_directional_edge_delta:
        reasons.append("directional edge degraded versus River")

    return ShadowPromotionGate(
        eligible_for_review=not reasons,
        reasons=tuple(reasons),
        observations=int(comparison.observations),
        score_delta=score_delta,
        accuracy_delta=accuracy_delta,
        brier_delta=brier_delta,
        directional_edge_delta=directional_edge_delta,
    )

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CalibrationRoutingPolicy:
    min_multiplier: float = 0.25
    ece_penalty_strength: float = 1.5
    min_observations: int = 20


def calibration_weight_multiplier(
    *,
    ece: float,
    observations: int,
    policy: CalibrationRoutingPolicy | None = None,
) -> float:
    policy = policy or CalibrationRoutingPolicy()
    if observations < policy.min_observations:
        return 1.0

    penalty = policy.ece_penalty_strength * max(0.0, float(ece))
    return max(policy.min_multiplier, min(1.0, 1.0 - penalty))

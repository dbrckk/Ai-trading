from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CrisisPolicy:
    cautious_stress_scale: float = 0.85
    defensive_stress_scale: float = 0.60
    preservation_stress_scale: float = 0.30
    cautious_drawdown: float = 0.04
    defensive_drawdown: float = 0.08
    preservation_drawdown: float = 0.12
    recover_drawdown: float = 0.03
    recovery_confirmations: int = 3


@dataclass(frozen=True)
class CrisisState:
    mode: str = "normal"
    recovery_streak: int = 0


@dataclass(frozen=True)
class CrisisDecision:
    state: CrisisState
    exposure_scale: float
    max_active_experts: int
    asset_limit_fraction: float
    allow_new_promotions: bool
    reason: str


_MODE_ORDER = {
    "normal": 0,
    "cautious": 1,
    "defensive": 2,
    "capital-preservation": 3,
}


def _desired_mode(
    *,
    stress_scale: float,
    drawdown: float,
    policy: CrisisPolicy,
) -> str:
    if (
        stress_scale <= policy.preservation_stress_scale
        or drawdown >= policy.preservation_drawdown
    ):
        return "capital-preservation"
    if (
        stress_scale <= policy.defensive_stress_scale
        or drawdown >= policy.defensive_drawdown
    ):
        return "defensive"
    if (
        stress_scale <= policy.cautious_stress_scale
        or drawdown >= policy.cautious_drawdown
    ):
        return "cautious"
    return "normal"


def evaluate_crisis_state(
    current: CrisisState,
    *,
    stress_scale: float,
    drawdown: float,
    policy: CrisisPolicy | None = None,
) -> CrisisDecision:
    policy = policy or CrisisPolicy()
    desired = _desired_mode(
        stress_scale=stress_scale,
        drawdown=drawdown,
        policy=policy,
    )

    current_rank = _MODE_ORDER[current.mode]
    desired_rank = _MODE_ORDER[desired]

    if desired_rank > current_rank:
        state = CrisisState(mode=desired, recovery_streak=0)
        reason = "risk conditions deteriorated"
    elif desired_rank < current_rank:
        healthy = (
            drawdown <= policy.recover_drawdown
            and stress_scale > policy.cautious_stress_scale
        )
        streak = current.recovery_streak + 1 if healthy else 0
        if streak >= policy.recovery_confirmations:
            next_rank = max(0, current_rank - 1)
            next_mode = next(k for k, v in _MODE_ORDER.items() if v == next_rank)
            state = CrisisState(mode=next_mode, recovery_streak=0)
            reason = "recovery confirmed with hysteresis"
        else:
            state = CrisisState(mode=current.mode, recovery_streak=streak)
            reason = "holding crisis mode until recovery confirmation"
    else:
        state = CrisisState(mode=current.mode, recovery_streak=0)
        reason = "mode unchanged"

    if state.mode == "normal":
        return CrisisDecision(state, 1.0, 8, 1.0, True, reason)
    if state.mode == "cautious":
        return CrisisDecision(state, 0.75, 5, 0.75, False, reason)
    if state.mode == "defensive":
        return CrisisDecision(state, 0.40, 3, 0.50, False, reason)
    return CrisisDecision(state, 0.10, 1, 0.25, False, reason)


def limits_for_state(state: CrisisState) -> CrisisDecision:
    if state.mode == "normal":
        return CrisisDecision(state, 1.0, 8, 1.0, True, "persisted normal mode")
    if state.mode == "cautious":
        return CrisisDecision(state, 0.75, 5, 0.75, False, "persisted cautious mode")
    if state.mode == "defensive":
        return CrisisDecision(state, 0.40, 3, 0.50, False, "persisted defensive mode")
    return CrisisDecision(
        state,
        0.10,
        1,
        0.25,
        False,
        "persisted capital-preservation mode",
    )

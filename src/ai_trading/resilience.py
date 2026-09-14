from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass(frozen=True)
class ResiliencePolicy:
    recovery_confirmations: int = 3
    cooldown_confirmations: int = 3


@dataclass(frozen=True)
class ResilienceState:
    mode: str = "NORMAL"
    healthy_streak: int = 0
    reason: str = "initial state"


@dataclass(frozen=True)
class ResilienceSignals:
    governor_verdict: str
    crisis_mode: str
    recovery_degraded: bool
    recovery_recent_failures: int
    recovery_fallback_depth: int


@dataclass(frozen=True)
class ResilienceDecision:
    state: ResilienceState
    exposure_cap: float
    promotions_allowed: bool
    scheduler_allowed: bool


class ResilienceStateStore:
    def __init__(self, path: str | Path = "artifacts/resilience_state.json") -> None:
        self.path = Path(path)

    def load(self) -> ResilienceState:
        if not self.path.exists():
            return ResilienceState()
        return ResilienceState(**json.loads(self.path.read_text(encoding="utf-8")))

    def save(self, state: ResilienceState) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temp = self.path.with_suffix(".tmp")
        temp.write_text(json.dumps(asdict(state), sort_keys=True), encoding="utf-8")
        temp.replace(self.path)


def evaluate_resilience(
    current: ResilienceState,
    signals: ResilienceSignals,
    policy: ResiliencePolicy | None = None,
) -> ResilienceDecision:
    policy = policy or ResiliencePolicy()

    critical = (
        signals.governor_verdict == "HALT"
        or signals.recovery_recent_failures >= 4
        or signals.recovery_fallback_depth >= 5
    )
    degraded = (
        signals.recovery_degraded
        or signals.governor_verdict in {"FREEZE", "FLATTEN"}
        or signals.crisis_mode in {"defensive", "capital-preservation"}
    )
    cautious = (
        signals.governor_verdict == "REDUCE"
        or signals.crisis_mode == "cautious"
    )
    healthy = (
        signals.governor_verdict == "TRADE"
        and signals.crisis_mode == "normal"
        and not signals.recovery_degraded
        and signals.recovery_recent_failures == 0
        and signals.recovery_fallback_depth == 0
    )

    if critical:
        state = ResilienceState(
            mode="HALT",
            healthy_streak=0,
            reason="critical resilience threshold breached",
        )
    elif current.mode == "HALT":
        if healthy:
            state = ResilienceState(
                mode="COOLDOWN",
                healthy_streak=1,
                reason="critical condition cleared; cooldown started",
            )
        else:
            state = ResilienceState(
                mode="HALT",
                healthy_streak=0,
                reason="holding halt until conditions normalize",
            )
    elif current.mode == "COOLDOWN":
        streak = current.healthy_streak + 1 if healthy else 0
        if not healthy:
            state = ResilienceState(
                mode="DEGRADED" if degraded else "CAUTIOUS",
                healthy_streak=0,
                reason="cooldown interrupted by renewed risk",
            )
        elif streak >= policy.cooldown_confirmations:
            state = ResilienceState(
                mode="NORMAL",
                healthy_streak=0,
                reason="cooldown completed",
            )
        else:
            state = ResilienceState(
                mode="COOLDOWN",
                healthy_streak=streak,
                reason="cooldown confirmation in progress",
            )
    elif degraded:
        state = ResilienceState(
            mode="DEGRADED",
            healthy_streak=0,
            reason="aggregate resilience degraded",
        )
    elif cautious:
        state = ResilienceState(
            mode="CAUTIOUS",
            healthy_streak=0,
            reason="elevated but non-critical resilience risk",
        )
    elif current.mode in {"DEGRADED", "CAUTIOUS", "RECOVERY"} and healthy:
        streak = current.healthy_streak + 1
        if streak >= policy.recovery_confirmations:
            state = ResilienceState(
                mode="NORMAL",
                healthy_streak=0,
                reason="recovery confirmed",
            )
        else:
            state = ResilienceState(
                mode="RECOVERY",
                healthy_streak=streak,
                reason="healthy confirmation in progress",
            )
    else:
        state = ResilienceState(
            mode="NORMAL",
            healthy_streak=0,
            reason="all resilience gates healthy",
        )

    limits = {
        "NORMAL": (1.0, True, True),
        "CAUTIOUS": (0.75, False, True),
        "DEGRADED": (0.35, False, True),
        "RECOVERY": (0.50, False, True),
        "HALT": (0.0, False, False),
        "COOLDOWN": (0.25, False, True),
    }
    exposure_cap, promotions_allowed, scheduler_allowed = limits[state.mode]
    return ResilienceDecision(
        state=state,
        exposure_cap=exposure_cap,
        promotions_allowed=promotions_allowed,
        scheduler_allowed=scheduler_allowed,
    )

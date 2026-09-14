from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass(frozen=True)
class ResiliencePolicy:
    recovery_confirmations: int = 3
    cooldown_confirmations: int = 3
    halt_recovery_failures: int = 4
    halt_recovery_fallback_depth: int = 5
    cautious_exposure_cap: float = 0.75
    degraded_exposure_cap: float = 0.35
    recovery_exposure_cap: float = 0.50
    cooldown_exposure_cap: float = 0.25


@dataclass(frozen=True)
class ResilienceContext:
    data_quality: float = 1.0
    drawdown: float = 0.0
    annualized_volatility: float = 0.0
    recent_incidents: int = 0


def adapt_resilience_policy(
    base: ResiliencePolicy,
    context: ResilienceContext,
) -> ResiliencePolicy:
    severity = 0
    if context.data_quality < 0.95:
        severity += 1
    if context.data_quality < 0.85:
        severity += 1
    if context.drawdown >= 0.08:
        severity += 1
    if context.drawdown >= 0.12:
        severity += 1
    if context.annualized_volatility >= 0.30:
        severity += 1
    if context.annualized_volatility >= 0.50:
        severity += 1
    if context.recent_incidents >= 2:
        severity += 1
    if context.recent_incidents >= 4:
        severity += 1

    if severity == 0:
        return base

    return ResiliencePolicy(
        recovery_confirmations=min(8, base.recovery_confirmations + severity // 2),
        cooldown_confirmations=min(8, base.cooldown_confirmations + severity // 2),
        halt_recovery_failures=max(2, base.halt_recovery_failures - severity // 3),
        halt_recovery_fallback_depth=max(
            3,
            base.halt_recovery_fallback_depth - severity // 3,
        ),
        cautious_exposure_cap=max(
            0.40,
            base.cautious_exposure_cap - 0.05 * severity,
        ),
        degraded_exposure_cap=max(
            0.15,
            base.degraded_exposure_cap - 0.025 * severity,
        ),
        recovery_exposure_cap=max(
            0.25,
            base.recovery_exposure_cap - 0.04 * severity,
        ),
        cooldown_exposure_cap=max(
            0.10,
            base.cooldown_exposure_cap - 0.02 * severity,
        ),
    )


@dataclass(frozen=True)
class ResilienceState:
    mode: str = "NORMAL"
    healthy_streak: int = 0
    reason: str = "initial state"
    mode_steps: int = 0


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
        or signals.recovery_recent_failures >= policy.halt_recovery_failures
        or signals.recovery_fallback_depth >= policy.halt_recovery_fallback_depth
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
            mode_steps=current.mode_steps + 1 if current.mode == "HALT" else 1,
        )
    elif current.mode == "HALT":
        if healthy:
            state = ResilienceState(
                mode="COOLDOWN",
                healthy_streak=1,
                reason="critical condition cleared; cooldown started",
                mode_steps=1,
            )
        else:
            state = ResilienceState(
                mode="HALT",
                healthy_streak=0,
                reason="holding halt until conditions normalize",
                mode_steps=current.mode_steps + 1,
            )
    elif current.mode == "COOLDOWN":
        streak = current.healthy_streak + 1 if healthy else 0
        if not healthy:
            next_mode = "DEGRADED" if degraded else "CAUTIOUS"
            state = ResilienceState(
                mode=next_mode,
                healthy_streak=0,
                reason="cooldown interrupted by renewed risk",
                mode_steps=1,
            )
        elif streak >= policy.cooldown_confirmations:
            state = ResilienceState(
                mode="NORMAL",
                healthy_streak=0,
                reason="cooldown completed",
                mode_steps=1,
            )
        else:
            state = ResilienceState(
                mode="COOLDOWN",
                healthy_streak=streak,
                reason="cooldown confirmation in progress",
                mode_steps=current.mode_steps + 1,
            )
    elif degraded:
        state = ResilienceState(
            mode="DEGRADED",
            healthy_streak=0,
            reason="aggregate resilience degraded",
            mode_steps=current.mode_steps + 1 if current.mode == "DEGRADED" else 1,
        )
    elif cautious:
        state = ResilienceState(
            mode="CAUTIOUS",
            healthy_streak=0,
            reason="elevated but non-critical resilience risk",
            mode_steps=current.mode_steps + 1 if current.mode == "CAUTIOUS" else 1,
        )
    elif current.mode in {"DEGRADED", "CAUTIOUS", "RECOVERY"} and healthy:
        streak = current.healthy_streak + 1
        if streak >= policy.recovery_confirmations:
            state = ResilienceState(
                mode="NORMAL",
                healthy_streak=0,
                reason="recovery confirmed",
                mode_steps=1,
            )
        else:
            state = ResilienceState(
                mode="RECOVERY",
                healthy_streak=streak,
                reason="healthy confirmation in progress",
                mode_steps=current.mode_steps + 1 if current.mode == "RECOVERY" else 1,
            )
    else:
        state = ResilienceState(
            mode="NORMAL",
            healthy_streak=0,
            reason="all resilience gates healthy",
            mode_steps=current.mode_steps + 1 if current.mode == "NORMAL" else 1,
        )

    limits = {
        "NORMAL": (1.0, True, True),
        "CAUTIOUS": (policy.cautious_exposure_cap, False, True),
        "DEGRADED": (policy.degraded_exposure_cap, False, True),
        "RECOVERY": (policy.recovery_exposure_cap, False, True),
        "HALT": (0.0, False, False),
        "COOLDOWN": (policy.cooldown_exposure_cap, False, True),
    }
    exposure_cap, promotions_allowed, scheduler_allowed = limits[state.mode]
    return ResilienceDecision(
        state=state,
        exposure_cap=exposure_cap,
        promotions_allowed=promotions_allowed,
        scheduler_allowed=scheduler_allowed,
    )

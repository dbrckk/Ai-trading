from __future__ import annotations

from dataclasses import dataclass

from .lifecycle_log import LifecycleEventLog


@dataclass(frozen=True)
class ResilienceStabilityPolicy:
    event_window: int = 30
    max_oscillations: int = 4
    max_recovery_streak_events: int = 6
    max_cooldowns: int = 3


@dataclass(frozen=True)
class ResilienceStability:
    status: str
    oscillations: int
    recovery_streak_events: int
    cooldown_count: int
    reasons: tuple[str, ...]


def evaluate_resilience_stability(
    lifecycle_log: LifecycleEventLog,
    policy: ResilienceStabilityPolicy | None = None,
) -> ResilienceStability:
    policy = policy or ResilienceStabilityPolicy()
    events = [
        event
        for event in lifecycle_log.list()
        if event.event == "resilience_transition"
    ][-policy.event_window :]

    modes = [str(event.metadata.get("to_mode", "")) for event in events]
    oscillations = 0
    for index in range(2, len(modes)):
        if modes[index] == modes[index - 2] and modes[index] != modes[index - 1]:
            oscillations += 1

    recovery_streak = 0
    for mode in reversed(modes):
        if mode != "RECOVERY":
            break
        recovery_streak += 1

    cooldown_count = sum(mode == "COOLDOWN" for mode in modes)

    reasons: list[str] = []
    if oscillations >= policy.max_oscillations:
        reasons.append("resilience mode oscillation threshold exceeded")
    if recovery_streak >= policy.max_recovery_streak_events:
        reasons.append("resilience recovery duration threshold exceeded")
    if cooldown_count >= policy.max_cooldowns:
        reasons.append("resilience cooldown frequency threshold exceeded")

    severe = (
        oscillations >= policy.max_oscillations * 2
        or recovery_streak >= policy.max_recovery_streak_events * 2
        or cooldown_count >= policy.max_cooldowns * 2
    )
    status = "critical" if severe else "degraded" if reasons else "stable"

    return ResilienceStability(
        status=status,
        oscillations=oscillations,
        recovery_streak_events=recovery_streak,
        cooldown_count=cooldown_count,
        reasons=tuple(reasons),
    )

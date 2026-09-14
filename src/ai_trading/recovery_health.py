from __future__ import annotations

from dataclasses import dataclass

from .lifecycle_log import LifecycleEventLog


@dataclass(frozen=True)
class RecoveryHealthPolicy:
    max_recent_failures: int = 2
    max_fallback_depth: int = 2
    recent_event_window: int = 20


@dataclass(frozen=True)
class RecoveryHealth:
    status: str
    recent_attempts: int
    recent_failures: int
    max_fallback_depth: int
    reasons: tuple[str, ...]


def evaluate_recovery_health(
    lifecycle_log: LifecycleEventLog,
    policy: RecoveryHealthPolicy | None = None,
) -> RecoveryHealth:
    policy = policy or RecoveryHealthPolicy()
    events = [
        event
        for event in lifecycle_log.list()
        if event.event in {"recovery_succeeded", "recovery_failed"}
    ]
    recent = events[-policy.recent_event_window :]
    recent_failures = sum(event.event == "recovery_failed" for event in recent)
    max_depth = max(
        (int(event.metadata.get("fallback_depth", 0)) for event in recent),
        default=0,
    )

    reasons: list[str] = []
    if recent_failures > policy.max_recent_failures:
        reasons.append("too many recent recovery failures")
    if max_depth > policy.max_fallback_depth:
        reasons.append("recovery fallback depth exceeds policy")

    return RecoveryHealth(
        status="degraded" if reasons else "healthy",
        recent_attempts=len(recent),
        recent_failures=recent_failures,
        max_fallback_depth=max_depth,
        reasons=tuple(reasons),
    )

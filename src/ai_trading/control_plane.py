from __future__ import annotations

from dataclasses import dataclass

from .crisis_state_store import CrisisStateStore
from .governor_state_store import GovernorStateStore


@dataclass(frozen=True)
class ControlPlaneStatus:
    governor_verdict: str
    governor_reason: str
    crisis_mode: str
    recovery_streak: int
    promotions_allowed: bool
    scheduler_should_run: bool


def read_control_plane(
    *,
    governor_store: GovernorStateStore | None = None,
    crisis_store: CrisisStateStore | None = None,
) -> ControlPlaneStatus:
    governor_store = governor_store or GovernorStateStore()
    crisis_store = crisis_store or CrisisStateStore()
    governor = governor_store.load()
    crisis = crisis_store.load()

    promotions = crisis.mode == "normal" and governor.verdict == "TRADE"
    scheduler_should_run = governor.verdict != "HALT"

    return ControlPlaneStatus(
        governor_verdict=governor.verdict,
        governor_reason=governor.reason,
        crisis_mode=crisis.mode,
        recovery_streak=crisis.recovery_streak,
        promotions_allowed=promotions,
        scheduler_should_run=scheduler_should_run,
    )

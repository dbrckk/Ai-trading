from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .audit_chain import verify_audit_chain
from .audit_integrity import verify_jsonl_audit
from .governor_state_store import GovernorState, GovernorStateStore
from .watchdog import HeartbeatStore, WatchdogPolicy, heartbeat_is_stale


@dataclass(frozen=True)
class WatchdogEnforcement:
    healthy: bool
    halted: bool
    reasons: tuple[str, ...]


def enforce_watchdog(
    *,
    heartbeat_store: HeartbeatStore,
    audit_path: str | Path,
    governor_store: GovernorStateStore,
    policy: WatchdogPolicy | None = None,
) -> WatchdogEnforcement:
    reasons: list[str] = []
    heartbeat = heartbeat_store.load()

    if heartbeat_is_stale(heartbeat, policy):
        reasons.append("heartbeat stale or missing")

    audit_path = Path(audit_path)
    if audit_path.exists():
        json_report = verify_jsonl_audit(audit_path)
        chain_report = verify_audit_chain(audit_path)
        if not json_report.valid:
            reasons.append("audit JSON integrity failed")
        if not chain_report.valid:
            reasons.append("audit hash chain failed")

    if reasons:
        previous = governor_store.load()
        governor_store.save(
            GovernorState(
                verdict="HALT",
                reason="watchdog enforcement: " + "; ".join(reasons),
                consecutive_halts=previous.consecutive_halts + 1,
            )
        )
        return WatchdogEnforcement(
            healthy=False,
            halted=True,
            reasons=tuple(reasons),
        )

    return WatchdogEnforcement(
        healthy=True,
        halted=False,
        reasons=(),
    )

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from .audit_chain import verify_audit_chain
from .audit_integrity import verify_jsonl_audit
from .governor_state_store import GovernorState, GovernorStateStore
from .state_snapshot import AtomicSnapshotStore


@dataclass(frozen=True)
class StartupCheckReport:
    ready: bool
    reasons: tuple[str, ...]
    snapshot_available: bool
    audit_valid: bool
    state_files_valid: bool


def run_startup_check(
    *,
    audit_path: str | Path,
    state_files: list[str | Path],
    snapshot_store: AtomicSnapshotStore,
    governor_store: GovernorStateStore,
) -> StartupCheckReport:
    reasons: list[str] = []

    audit_path = Path(audit_path)
    if audit_path.exists():
        json_report = verify_jsonl_audit(audit_path)
        chain_report = verify_audit_chain(audit_path)
        audit_valid = json_report.valid and chain_report.valid
        if not audit_valid:
            reasons.append("audit integrity check failed")
    else:
        audit_valid = True

    state_files_valid = True
    for item in state_files:
        path = Path(item)
        if not path.exists():
            continue
        try:
            json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            state_files_valid = False
            reasons.append(f"invalid state file: {path.name}")

    snapshot_available = snapshot_store.latest_valid() is not None
    ready = audit_valid and state_files_valid

    if not ready:
        governor_store.save(
            GovernorState(
                verdict="HALT",
                reason="startup self-check failed: " + "; ".join(reasons),
                consecutive_halts=1,
            )
        )

    return StartupCheckReport(
        ready=ready,
        reasons=tuple(reasons),
        snapshot_available=snapshot_available,
        audit_valid=audit_valid,
        state_files_valid=state_files_valid,
    )

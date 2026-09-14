from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .checkpoint_verification import verify_checkpoint_state
from .state_snapshot import AtomicSnapshotStore


@dataclass(frozen=True)
class RecoveryResult:
    restored: bool
    snapshot: str | None
    reason: str
    verified: bool = False
    mismatches: tuple[str, ...] = ()


def recover_latest_consistent_state(
    snapshot_store: AtomicSnapshotStore,
    *,
    destination_root: str | Path = "artifacts",
    audit_path: str | Path | None = None,
    state_files: list[str | Path] | None = None,
) -> RecoveryResult:
    latest = snapshot_store.latest_valid()
    if latest is None:
        return RecoveryResult(
            restored=False,
            snapshot=None,
            reason="no valid snapshot available",
        )

    restored = snapshot_store.restore_latest(destination_root)

    if audit_path is None or state_files is None:
        return RecoveryResult(
            restored=True,
            snapshot=str(restored),
            reason="restored latest valid atomic snapshot",
            verified=False,
        )

    verification = verify_checkpoint_state(
        audit_path,
        restored,
        state_files,
    )
    if not verification.valid:
        return RecoveryResult(
            restored=False,
            snapshot=str(restored),
            reason=verification.reason,
            verified=False,
            mismatches=verification.mismatches,
        )

    return RecoveryResult(
        restored=True,
        snapshot=str(restored),
        reason="restored and verified latest atomic snapshot",
        verified=True,
        mismatches=(),
    )

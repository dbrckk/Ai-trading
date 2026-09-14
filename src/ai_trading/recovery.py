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
    candidates = snapshot_store.valid_snapshots()
    if not candidates:
        return RecoveryResult(
            restored=False,
            snapshot=None,
            reason="no valid snapshot available",
        )

    if audit_path is None or state_files is None:
        restored = snapshot_store.restore_snapshot(candidates[0], destination_root)
        return RecoveryResult(
            restored=True,
            snapshot=str(restored),
            reason="restored latest valid atomic snapshot",
            verified=False,
        )

    last_reason = "no logically consistent snapshot available"
    last_mismatches: tuple[str, ...] = ()
    last_snapshot: str | None = None

    for candidate in candidates:
        restored = snapshot_store.restore_snapshot(candidate, destination_root)
        verification = verify_checkpoint_state(
            audit_path,
            restored,
            state_files,
        )
        if verification.valid:
            return RecoveryResult(
                restored=True,
                snapshot=str(restored),
                reason="restored and verified consistent atomic snapshot",
                verified=True,
                mismatches=(),
            )
        last_reason = verification.reason
        last_mismatches = verification.mismatches
        last_snapshot = str(restored)

    return RecoveryResult(
        restored=False,
        snapshot=last_snapshot,
        reason=last_reason,
        verified=False,
        mismatches=last_mismatches,
    )

from __future__ import annotations

import shutil
import tempfile
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

    tracked_paths = [Path(path) for path in state_files]
    with tempfile.TemporaryDirectory(prefix="ai-trading-recovery-") as temp_dir_name:
        temp_dir = Path(temp_dir_name)
        backups: dict[Path, Path | None] = {}
        for index, path in enumerate(tracked_paths):
            if path.exists() and path.is_file():
                backup = temp_dir / f"{index}.bak"
                shutil.copy2(path, backup)
                backups[path] = backup
            else:
                backups[path] = None

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

        for path, backup in backups.items():
            if backup is None:
                path.unlink(missing_ok=True)
                continue
            path.parent.mkdir(parents=True, exist_ok=True)
            restore_temp = path.with_suffix(path.suffix + ".rollback.tmp")
            shutil.copy2(backup, restore_temp)
            restore_temp.replace(path)

    return RecoveryResult(
        restored=False,
        snapshot=last_snapshot,
        reason=last_reason,
        verified=False,
        mismatches=last_mismatches,
    )

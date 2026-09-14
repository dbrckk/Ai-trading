from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from .state_hash import file_state_hash


@dataclass(frozen=True)
class CheckpointVerification:
    valid: bool
    matched_checkpoint: bool
    reason: str
    mismatches: tuple[str, ...]


def verify_checkpoint_state(
    audit_path: str | Path,
    snapshot_path: str | Path,
    state_files: list[str | Path],
) -> CheckpointVerification:
    audit_path = Path(audit_path)
    snapshot_path = str(snapshot_path)

    if not audit_path.exists():
        return CheckpointVerification(
            False,
            False,
            "audit file missing",
            (),
        )

    checkpoint = None
    with audit_path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            record = json.loads(line)
            if record.get("event") != "session_checkpoint":
                continue
            payload = record.get("payload", {})
            if str(payload.get("snapshot")) == snapshot_path:
                checkpoint = payload

    if checkpoint is None:
        return CheckpointVerification(
            False,
            False,
            "matching session checkpoint not found",
            (),
        )

    expected = checkpoint.get("state_hashes", {})
    mismatches: list[str] = []
    for state_file in state_files:
        path = Path(state_file)
        name = path.name
        actual = file_state_hash(path)
        if expected.get(name) != actual:
            mismatches.append(name)

    return CheckpointVerification(
        valid=not mismatches,
        matched_checkpoint=True,
        reason=(
            "restored state matches checkpoint"
            if not mismatches
            else "restored state hash mismatch"
        ),
        mismatches=tuple(mismatches),
    )

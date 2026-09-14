from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

from .state_hash import file_state_hash


@dataclass(frozen=True)
class SessionFingerprint:
    fingerprint: str
    state_hashes: dict[str, str]
    audit_tail_hash: str


def _audit_tail_hash(path: Path) -> str:
    if not path.exists():
        return "MISSING"
    last = ""
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                last = line
    if not last:
        return "EMPTY"
    try:
        record = json.loads(last)
    except json.JSONDecodeError:
        return "INVALID"
    return str(record.get("hash", "LEGACY"))


def compute_session_fingerprint(
    state_files: list[str | Path],
    audit_path: str | Path,
) -> SessionFingerprint:
    hashes = {
        Path(path).name: file_state_hash(path)
        for path in state_files
    }
    audit_tail = _audit_tail_hash(Path(audit_path))
    payload = {
        "audit_tail_hash": audit_tail,
        "state_hashes": hashes,
    }
    canonical = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
    )
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return SessionFingerprint(
        fingerprint=digest,
        state_hashes=hashes,
        audit_tail_hash=audit_tail,
    )

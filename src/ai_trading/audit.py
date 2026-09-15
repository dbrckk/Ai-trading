from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


def _record_hash(record: dict[str, Any]) -> str:
    canonical = json.dumps(record, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def build_audit_record(
    event: str,
    payload: dict[str, Any],
    prev_hash: str,
    *,
    timestamp_utc: str | None = None,
) -> dict[str, Any]:
    body = {
        "timestamp_utc": timestamp_utc or datetime.now(UTC).isoformat(),
        "event": event,
        "payload": payload,
        "prev_hash": prev_hash,
    }
    return {**body, "hash": _record_hash(body)}


class AuditLog:
    def __init__(self, path: str | Path = "artifacts/audit.jsonl") -> None:
        self.path = Path(path)

    def _last_hash(self) -> str:
        if not self.path.exists():
            return "GENESIS"
        last_non_empty = ""
        with self.path.open("r", encoding="utf-8") as handle:
            for line in handle:
                if line.strip():
                    last_non_empty = line
        if not last_non_empty:
            return "GENESIS"
        try:
            record = json.loads(last_non_empty)
        except json.JSONDecodeError:
            return "CORRUPT"
        return str(record.get("hash", "LEGACY"))

    def append(self, event: str, payload: dict[str, Any]) -> dict[str, Any]:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        record = build_audit_record(event, payload, self._last_hash())
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, sort_keys=True, default=str) + "\n")
        return record

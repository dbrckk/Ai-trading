from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


def _record_hash(record: dict[str, Any]) -> str:
    canonical = json.dumps(record, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


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
        body = {
            "timestamp_utc": datetime.now(UTC).isoformat(),
            "event": event,
            "payload": payload,
            "prev_hash": self._last_hash(),
        }
        record = {**body, "hash": _record_hash(body)}
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, sort_keys=True, default=str) + "\n")
        return record

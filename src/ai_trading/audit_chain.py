from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class AuditChainReport:
    valid: bool
    lines: int
    invalid_line: int | None
    reason: str


def _record_hash(record: dict[str, Any]) -> str:
    canonical = json.dumps(record, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def verify_audit_chain(path: str | Path) -> AuditChainReport:
    path = Path(path)
    if not path.exists():
        return AuditChainReport(False, 0, None, "audit file missing")

    expected_prev = "GENESIS"
    lines = 0

    with path.open("r", encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                return AuditChainReport(False, lines, line_no, "invalid JSON")

            if "hash" not in record or "prev_hash" not in record:
                return AuditChainReport(
                    False,
                    lines,
                    line_no,
                    "missing audit chain fields",
                )

            if record["prev_hash"] != expected_prev:
                return AuditChainReport(
                    False,
                    lines,
                    line_no,
                    "previous hash mismatch",
                )

            stored_hash = str(record["hash"])
            body = {k: v for k, v in record.items() if k != "hash"}
            computed = _record_hash(body)
            if stored_hash != computed:
                return AuditChainReport(
                    False,
                    lines,
                    line_no,
                    "record hash mismatch",
                )

            expected_prev = stored_hash
            lines += 1

    return AuditChainReport(True, lines, None, "valid hash chain")

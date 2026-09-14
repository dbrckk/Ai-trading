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
    legacy_lines: int = 0


def _record_hash(record: dict[str, Any]) -> str:
    canonical = json.dumps(record, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def verify_audit_chain(path: str | Path) -> AuditChainReport:
    path = Path(path)
    if not path.exists():
        return AuditChainReport(False, 0, None, "audit file missing")

    expected_prev = "GENESIS"
    lines = 0
    legacy_lines = 0
    chain_started = False

    with path.open("r", encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                return AuditChainReport(
                    False,
                    lines,
                    line_no,
                    "invalid JSON",
                    legacy_lines,
                )

            has_chain_fields = "hash" in record and "prev_hash" in record
            if not has_chain_fields:
                if chain_started:
                    return AuditChainReport(
                        False,
                        lines,
                        line_no,
                        "unchained record after hash chain started",
                        legacy_lines,
                    )
                legacy_lines += 1
                lines += 1
                expected_prev = "LEGACY"
                continue

            chain_started = True
            if record["prev_hash"] != expected_prev:
                return AuditChainReport(
                    False,
                    lines,
                    line_no,
                    "previous hash mismatch",
                    legacy_lines,
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
                    legacy_lines,
                )

            expected_prev = stored_hash
            lines += 1

    reason = (
        "valid hash chain"
        if legacy_lines == 0
        else f"valid chain after {legacy_lines} legacy records"
    )
    return AuditChainReport(True, lines, None, reason, legacy_lines)

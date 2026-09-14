from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path


@dataclass(frozen=True)
class AuditIntegrityReport:
    valid: bool
    lines: int
    checksum: str
    invalid_line: int | None


def verify_jsonl_audit(path: str | Path) -> AuditIntegrityReport:
    path = Path(path)
    if not path.exists():
        return AuditIntegrityReport(False, 0, "", None)

    digest = hashlib.sha256()
    lines = 0
    with path.open("rb") as raw:
        for line_no, raw_line in enumerate(raw, start=1):
            digest.update(raw_line)
            if not raw_line.strip():
                continue
            try:
                json.loads(raw_line.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError):
                return AuditIntegrityReport(
                    False,
                    lines,
                    digest.hexdigest(),
                    line_no,
                )
            lines += 1

    return AuditIntegrityReport(True, lines, digest.hexdigest(), None)

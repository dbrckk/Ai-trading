from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path


@dataclass(frozen=True)
class RevocationRecord:
    release_hash: str
    revoked_at_utc: str
    reason: str


class ReadinessRevocationStore:
    def __init__(
        self,
        path: str | Path = "artifacts/readiness_revocations.jsonl",
    ) -> None:
        self.path = Path(path)

    def revoke(self, release_hash: str, *, reason: str) -> RevocationRecord:
        existing = {record.release_hash for record in self.list()}
        if release_hash in existing:
            return next(record for record in self.list() if record.release_hash == release_hash)

        record = RevocationRecord(
            release_hash=release_hash,
            revoked_at_utc=datetime.now(UTC).isoformat(),
            reason=reason,
        )
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(asdict(record), sort_keys=True) + "\n")
        return record

    def is_revoked(self, release_hash: str) -> bool:
        return any(record.release_hash == release_hash for record in self.list())

    def list(self) -> list[RevocationRecord]:
        if not self.path.exists():
            return []
        records: list[RevocationRecord] = []
        with self.path.open("r", encoding="utf-8") as handle:
            for line in handle:
                if line.strip():
                    records.append(RevocationRecord(**json.loads(line)))
        return records

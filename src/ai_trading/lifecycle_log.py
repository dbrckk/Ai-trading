from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class LifecycleEvent:
    event: str
    version: str
    model_name: str
    reason: str
    failure_type: str
    processed_bar: int
    artifact_sha256: str | None
    metadata: dict[str, Any]
    created_at_utc: str


class LifecycleEventLog:
    def __init__(self, path: str | Path = "artifacts/model_lifecycle.jsonl") -> None:
        self.path = Path(path)

    def append(
        self,
        *,
        event: str,
        version: str,
        model_name: str,
        reason: str = "",
        failure_type: str = "",
        processed_bar: int = 0,
        artifact_path: str | Path | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> LifecycleEvent:
        artifact_hash = (
            sha256_file(artifact_path)
            if artifact_path is not None and Path(artifact_path).exists()
            else None
        )
        record = LifecycleEvent(
            event=event,
            version=version,
            model_name=model_name,
            reason=reason,
            failure_type=failure_type,
            processed_bar=int(processed_bar),
            artifact_sha256=artifact_hash,
            metadata=metadata or {},
            created_at_utc=datetime.now(UTC).isoformat(),
        )
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(asdict(record), sort_keys=True) + "\n")
        return record

    def list(self) -> list[LifecycleEvent]:
        if not self.path.exists():
            return []
        records: list[LifecycleEvent] = []
        with self.path.open("r", encoding="utf-8") as handle:
            for line in handle:
                if line.strip():
                    records.append(LifecycleEvent(**json.loads(line)))
        return records


def sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()

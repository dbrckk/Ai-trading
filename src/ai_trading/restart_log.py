from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path


@dataclass(frozen=True)
class RestartEvent:
    timestamp_utc: str
    exit_code: int | None
    runtime_seconds: float
    restart_index: int
    reason: str


class RestartLog:
    def __init__(self, path: str | Path = "artifacts/restarts.jsonl") -> None:
        self.path = Path(path)

    def append(
        self,
        *,
        exit_code: int | None,
        runtime_seconds: float,
        restart_index: int,
        reason: str,
    ) -> RestartEvent:
        event = RestartEvent(
            timestamp_utc=datetime.now(UTC).isoformat(),
            exit_code=exit_code,
            runtime_seconds=float(runtime_seconds),
            restart_index=int(restart_index),
            reason=reason,
        )
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(event.__dict__, sort_keys=True) + "\n")
        return event

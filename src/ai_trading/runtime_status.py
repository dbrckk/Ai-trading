from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path


@dataclass(frozen=True)
class HostedRuntimeStatus:
    engine_status: str
    symbol: str
    interval: str
    updated_at_utc: str
    last_cycle_timestamp: str | None = None
    processed: bool = False
    side: int = 0
    confidence: float = 0.0
    approved: bool = False
    reason: str = ""
    equity: float = 0.0
    units: float = 0.0
    processed_bars: int = 0
    error: str | None = None
    poll_seconds: float = 60.0
    consecutive_cycle_errors: int = 0
    cycle_duration_seconds: float | None = None
    mtf_evaluated: bool = False


def runtime_status_snapshot(
    status: HostedRuntimeStatus | None,
    *,
    now: datetime | None = None,
) -> dict[str, object]:
    if status is None:
        return {
            "engine_status": "OFF",
            "engine_healthy": False,
            "heartbeat_age_seconds": None,
            "heartbeat_stale_after_seconds": None,
            "updated_at_utc": None,
        }

    current_time = now or datetime.now(UTC)
    if current_time.tzinfo is None:
        current_time = current_time.replace(tzinfo=UTC)
    else:
        current_time = current_time.astimezone(UTC)

    stale_after_seconds = max(30.0, status.poll_seconds * 3.0)
    heartbeat_age_seconds: float | None
    heartbeat_stale = False
    try:
        heartbeat_time = datetime.fromisoformat(status.updated_at_utc)
        if heartbeat_time.tzinfo is None:
            heartbeat_time = heartbeat_time.replace(tzinfo=UTC)
        else:
            heartbeat_time = heartbeat_time.astimezone(UTC)
        heartbeat_age_seconds = max(
            0.0,
            (current_time - heartbeat_time).total_seconds(),
        )
        heartbeat_stale = heartbeat_age_seconds > stale_after_seconds
    except ValueError:
        heartbeat_age_seconds = None
        heartbeat_stale = True

    engine_status = status.engine_status
    if heartbeat_stale and engine_status in {"STARTING", "RUNNING"}:
        engine_status = "STALE"

    payload: dict[str, object] = asdict(status)
    payload.update(
        {
            "engine_status": engine_status,
            "engine_healthy": engine_status == "RUNNING",
            "heartbeat_age_seconds": heartbeat_age_seconds,
            "heartbeat_stale_after_seconds": stale_after_seconds,
        }
    )
    return payload


class HostedRuntimeStatusStore:
    def __init__(self, path: str | Path = "artifacts/runtime_status.json") -> None:
        self.path = Path(path)

    def load(self) -> HostedRuntimeStatus | None:
        if not self.path.exists():
            return None
        return HostedRuntimeStatus(**json.loads(self.path.read_text(encoding="utf-8")))

    def save(self, status: HostedRuntimeStatus) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temp = self.path.with_suffix(".tmp")
        temp.write_text(json.dumps(asdict(status), sort_keys=True), encoding="utf-8")
        temp.replace(self.path)

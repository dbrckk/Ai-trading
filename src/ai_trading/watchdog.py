from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import UTC, datetime
import json
from pathlib import Path


@dataclass(frozen=True)
class Heartbeat:
    component: str
    timestamp_utc: str
    iteration: int
    status: str


@dataclass(frozen=True)
class WatchdogPolicy:
    max_heartbeat_age_seconds: float = 180.0


class HeartbeatStore:
    def __init__(self, path: str | Path = "artifacts/heartbeat.json") -> None:
        self.path = Path(path)

    def write(self, component: str, iteration: int, status: str = "ok") -> Heartbeat:
        hb = Heartbeat(
            component=component,
            timestamp_utc=datetime.now(UTC).isoformat(),
            iteration=int(iteration),
            status=status,
        )
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temp = self.path.with_suffix(".tmp")
        temp.write_text(json.dumps(asdict(hb), sort_keys=True), encoding="utf-8")
        temp.replace(self.path)
        return hb

    def load(self) -> Heartbeat | None:
        if not self.path.exists():
            return None
        return Heartbeat(**json.loads(self.path.read_text(encoding="utf-8")))


def heartbeat_age_seconds(heartbeat: Heartbeat, *, now: datetime | None = None) -> float:
    now = now or datetime.now(UTC)
    timestamp = datetime.fromisoformat(heartbeat.timestamp_utc)
    return max(0.0, (now - timestamp).total_seconds())


def heartbeat_is_stale(
    heartbeat: Heartbeat | None,
    policy: WatchdogPolicy | None = None,
) -> bool:
    policy = policy or WatchdogPolicy()
    if heartbeat is None:
        return True
    return heartbeat_age_seconds(heartbeat) > policy.max_heartbeat_age_seconds

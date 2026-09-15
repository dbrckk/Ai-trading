from __future__ import annotations

import json
from dataclasses import asdict, dataclass
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

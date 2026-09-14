from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass(frozen=True)
class MaintenanceState:
    enabled: bool = False
    reason: str = ""


class MaintenanceStore:
    def __init__(self, path: str | Path = "artifacts/maintenance.json") -> None:
        self.path = Path(path)

    def load(self) -> MaintenanceState:
        if not self.path.exists():
            return MaintenanceState()
        return MaintenanceState(**json.loads(self.path.read_text(encoding="utf-8")))

    def save(self, state: MaintenanceState) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temp = self.path.with_suffix(".tmp")
        temp.write_text(json.dumps(asdict(state), sort_keys=True), encoding="utf-8")
        temp.replace(self.path)

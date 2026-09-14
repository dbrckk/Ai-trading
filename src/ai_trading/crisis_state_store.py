from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from .crisis_controller import CrisisState


class CrisisStateStore:
    def __init__(self, path: str | Path = "artifacts/crisis_state.json") -> None:
        self.path = Path(path)

    def load(self) -> CrisisState:
        if not self.path.exists():
            return CrisisState()
        payload = json.loads(self.path.read_text(encoding="utf-8"))
        return CrisisState(**payload)

    def save(self, state: CrisisState) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temp = self.path.with_suffix(".tmp")
        temp.write_text(json.dumps(asdict(state), sort_keys=True), encoding="utf-8")
        temp.replace(self.path)

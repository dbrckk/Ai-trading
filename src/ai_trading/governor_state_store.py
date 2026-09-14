from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass(frozen=True)
class GovernorState:
    verdict: str = "TRADE"
    reason: str = "initial state"
    consecutive_halts: int = 0


class GovernorStateStore:
    def __init__(self, path: str | Path = "artifacts/risk_governor_state.json") -> None:
        self.path = Path(path)

    def load(self) -> GovernorState:
        if not self.path.exists():
            return GovernorState()
        payload = json.loads(self.path.read_text(encoding="utf-8"))
        return GovernorState(**payload)

    def save(self, state: GovernorState) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temp = self.path.with_suffix(".tmp")
        temp.write_text(json.dumps(asdict(state), sort_keys=True), encoding="utf-8")
        temp.replace(self.path)

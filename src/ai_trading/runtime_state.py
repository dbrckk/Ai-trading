from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass
class RuntimeState:
    cash: float
    units: float
    last_price: float
    peak_equity: float
    day_start_equity: float
    last_processed: str | None = None
    processed_bars: int = 0
    last_learning_cycle_bar: int = 0


class RuntimeStateStore:
    def __init__(self, path: str | Path = "artifacts/runtime_state.json") -> None:
        self.path = Path(path)

    def load(self, starting_cash: float) -> RuntimeState:
        if not self.path.exists():
            return RuntimeState(
                cash=starting_cash,
                units=0.0,
                last_price=0.0,
                peak_equity=starting_cash,
                day_start_equity=starting_cash,
            )
        return RuntimeState(**json.loads(self.path.read_text(encoding="utf-8")))

    def save(self, state: RuntimeState) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temp = self.path.with_suffix(".tmp")
        temp.write_text(json.dumps(asdict(state), sort_keys=True), encoding="utf-8")
        temp.replace(self.path)

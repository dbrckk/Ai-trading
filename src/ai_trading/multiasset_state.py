from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path


@dataclass
class AssetPosition:
    units: float = 0.0
    last_price: float = 0.0


@dataclass
class MultiAssetState:
    cash: float
    peak_equity: float
    day_start_equity: float
    positions: dict[str, AssetPosition] = field(default_factory=dict)
    last_processed: str | None = None
    processed_bars: int = 0

    def equity(self) -> float:
        return self.cash + sum(p.units * p.last_price for p in self.positions.values())


class MultiAssetStateStore:
    def __init__(self, path: str | Path = "artifacts/multiasset_state.json") -> None:
        self.path = Path(path)

    def load(self, starting_cash: float) -> MultiAssetState:
        if not self.path.exists():
            return MultiAssetState(
                cash=starting_cash,
                peak_equity=starting_cash,
                day_start_equity=starting_cash,
            )
        payload = json.loads(self.path.read_text(encoding="utf-8"))
        payload["positions"] = {
            symbol: AssetPosition(**position)
            for symbol, position in payload.get("positions", {}).items()
        }
        return MultiAssetState(**payload)

    def save(self, state: MultiAssetState) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temp = self.path.with_suffix(".tmp")
        temp.write_text(json.dumps(asdict(state), sort_keys=True), encoding="utf-8")
        temp.replace(self.path)

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from .economic_meta import EconomicMetaConfig, EconomicMetaStats, update_economic_meta


class EconomicMetaStore:
    def __init__(self, path: str | Path = "artifacts/economic_meta.json") -> None:
        self.path = Path(path)

    def load(self) -> dict[str, EconomicMetaStats]:
        if not self.path.exists():
            return {}
        payload = json.loads(self.path.read_text(encoding="utf-8"))
        return {key: EconomicMetaStats(**value) for key, value in payload.items()}

    def save(self, data: dict[str, EconomicMetaStats]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temp = self.path.with_suffix(".tmp")
        temp.write_text(
            json.dumps({k: asdict(v) for k, v in data.items()}, sort_keys=True),
            encoding="utf-8",
        )
        temp.replace(self.path)

    def update(
        self,
        key: str,
        *,
        pnl: float,
        turnover: float,
        costs: float,
        drawdown: float,
        equity: float,
        config: EconomicMetaConfig | None = None,
    ) -> EconomicMetaStats:
        data = self.load()
        current = data.get(key, EconomicMetaStats())
        updated = update_economic_meta(
            current,
            pnl=pnl,
            turnover=turnover,
            costs=costs,
            drawdown=drawdown,
            equity=equity,
            config=config,
        )
        data[key] = updated
        self.save(data)
        return updated

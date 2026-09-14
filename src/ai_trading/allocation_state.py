from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import pandas as pd


@dataclass(frozen=True)
class AllocationState:
    weights: dict[str, float]


class AllocationStateStore:
    def __init__(self, path: str | Path = "artifacts/global_allocation.json") -> None:
        self.path = Path(path)

    def load(self) -> pd.Series:
        if not self.path.exists():
            return pd.Series(dtype=float)
        payload = json.loads(self.path.read_text(encoding="utf-8"))
        return pd.Series(payload.get("weights", {}), dtype=float)

    def save(self, weights: pd.Series) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temp = self.path.with_suffix(".tmp")
        temp.write_text(
            json.dumps({"weights": {str(k): float(v) for k, v in weights.items()}}, sort_keys=True),
            encoding="utf-8",
        )
        temp.replace(self.path)

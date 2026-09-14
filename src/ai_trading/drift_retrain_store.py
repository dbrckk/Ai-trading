from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass(frozen=True)
class DriftRetrainRecord:
    processed_bar: int
    max_psi: float
    correlation_shift: float


class DriftRetrainStore:
    def __init__(
        self,
        path: str | Path = "artifacts/drift_retrain.json",
    ) -> None:
        self.path = Path(path)

    def load(self) -> dict[str, DriftRetrainRecord]:
        if not self.path.exists():
            return {}
        payload = json.loads(self.path.read_text(encoding="utf-8"))
        return {
            symbol: DriftRetrainRecord(**record)
            for symbol, record in payload.items()
        }

    def should_retrain(
        self,
        symbol: str,
        *,
        processed_bar: int,
        cooldown_bars: int = 20,
    ) -> bool:
        record = self.load().get(symbol)
        if record is None:
            return True
        return processed_bar - record.processed_bar >= cooldown_bars

    def mark(
        self,
        symbol: str,
        *,
        processed_bar: int,
        max_psi: float,
        correlation_shift: float,
    ) -> None:
        records = self.load()
        records[symbol] = DriftRetrainRecord(
            processed_bar=int(processed_bar),
            max_psi=float(max_psi),
            correlation_shift=float(correlation_shift),
        )
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temp = self.path.with_suffix(".tmp")
        temp.write_text(
            json.dumps(
                {key: asdict(value) for key, value in records.items()},
                sort_keys=True,
            ),
            encoding="utf-8",
        )
        temp.replace(self.path)

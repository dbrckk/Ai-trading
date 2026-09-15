from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass(frozen=True)
class TradeSnapshot:
    timestamp_utc: str
    symbol: str
    side: str
    quantity: float
    price: float
    status: str
    pnl: float = 0.0
    confidence: float | None = None
    strategy: str = ""


class TradeJournal:
    """Append-only JSONL journal used as the dashboard's stable event boundary."""

    def __init__(self, path: str | Path = "artifacts/trades.jsonl") -> None:
        self.path = Path(path)

    def append(self, trade: TradeSnapshot) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(asdict(trade), sort_keys=True) + "\n")

    def list(self, *, limit: int | None = None) -> tuple[TradeSnapshot, ...]:
        if not self.path.exists():
            return ()
        rows: list[TradeSnapshot] = []
        with self.path.open(encoding="utf-8") as handle:
            for line in handle:
                if line.strip():
                    rows.append(TradeSnapshot(**json.loads(line)))
        if limit is not None:
            rows = rows[-limit:]
        return tuple(rows)

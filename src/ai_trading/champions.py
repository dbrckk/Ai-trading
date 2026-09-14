from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class ChampionRecord:
    version: str
    model_name: str
    score: float
    metrics: dict[str, float]
    config: dict[str, Any]
    promoted_at_utc: str
    active: bool = True


class ChampionRegistry:
    def __init__(self, path: str | Path = "artifacts/champions.jsonl") -> None:
        self.path = Path(path)

    def _read(self) -> list[ChampionRecord]:
        if not self.path.exists():
            return []
        records: list[ChampionRecord] = []
        with self.path.open("r", encoding="utf-8") as handle:
            for line in handle:
                if line.strip():
                    records.append(ChampionRecord(**json.loads(line)))
        return records

    def list(self) -> list[ChampionRecord]:
        return self._read()

    def active(self) -> ChampionRecord | None:
        for record in reversed(self._read()):
            if record.active:
                return record
        return None

    def promote(
        self,
        *,
        version: str,
        model_name: str,
        score: float,
        metrics: dict[str, float],
        config: dict[str, Any],
    ) -> ChampionRecord:
        records = self._read()
        updated = [ChampionRecord(**{**asdict(r), "active": False}) for r in records]
        promoted = ChampionRecord(
            version=version,
            model_name=model_name,
            score=float(score),
            metrics={k: float(v) for k, v in metrics.items()},
            config=config,
            promoted_at_utc=datetime.now(UTC).isoformat(),
            active=True,
        )
        updated.append(promoted)
        self._write(updated)
        return promoted

    def rollback(self) -> ChampionRecord:
        records = self._read()
        active_idx = next((i for i in range(len(records) - 1, -1, -1) if records[i].active), None)
        if active_idx is None:
            raise RuntimeError("No active champion")
        if active_idx == 0:
            raise RuntimeError("No previous champion available for rollback")

        updated = [ChampionRecord(**{**asdict(r), "active": False}) for r in records]
        previous = updated[active_idx - 1]
        rolled_back = ChampionRecord(**{**asdict(previous), "active": True})
        updated[active_idx - 1] = rolled_back
        self._write(updated)
        return rolled_back

    def _write(self, records: list[ChampionRecord]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("w", encoding="utf-8") as handle:
            for record in records:
                handle.write(json.dumps(asdict(record), sort_keys=True) + "\n")

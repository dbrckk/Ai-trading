from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path


@dataclass(frozen=True)
class LineageRecord:
    expert: str
    parent: str | None
    generation: int
    created_at_utc: str


@dataclass(frozen=True)
class GenerationSnapshot:
    generation: int
    active_experts: tuple[str, ...]
    portfolio_score: float
    created_at_utc: str
    rolled_back: bool = False


class GenerationStore:
    def __init__(
        self,
        lineage_path: str | Path = "artifacts/expert_lineage.json",
        generations_path: str | Path = "artifacts/generations.jsonl",
    ) -> None:
        self.lineage_path = Path(lineage_path)
        self.generations_path = Path(generations_path)

    def load_lineage(self) -> dict[str, LineageRecord]:
        if not self.lineage_path.exists():
            return {}
        payload = json.loads(self.lineage_path.read_text(encoding="utf-8"))
        return {name: LineageRecord(**value) for name, value in payload.items()}

    def add_lineage(self, expert: str, parent: str | None, generation: int) -> LineageRecord:
        data = self.load_lineage()
        record = LineageRecord(
            expert=expert,
            parent=parent,
            generation=int(generation),
            created_at_utc=datetime.now(UTC).isoformat(),
        )
        data[expert] = record
        self.lineage_path.parent.mkdir(parents=True, exist_ok=True)
        temp = self.lineage_path.with_suffix(".tmp")
        temp.write_text(
            json.dumps({k: asdict(v) for k, v in data.items()}, sort_keys=True),
            encoding="utf-8",
        )
        temp.replace(self.lineage_path)
        return record

    def snapshots(self) -> list[GenerationSnapshot]:
        if not self.generations_path.exists():
            return []
        snapshots: list[GenerationSnapshot] = []
        for line in self.generations_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            payload = json.loads(line)
            payload["active_experts"] = tuple(payload.get("active_experts", ()))
            snapshots.append(GenerationSnapshot(**payload))
        return snapshots

    def current_generation(self) -> int:
        snapshots = self.snapshots()
        return snapshots[-1].generation if snapshots else 0

    def snapshot(self, active_experts: list[str], portfolio_score: float) -> GenerationSnapshot:
        record = GenerationSnapshot(
            generation=self.current_generation() + 1,
            active_experts=tuple(sorted(active_experts)),
            portfolio_score=float(portfolio_score),
            created_at_utc=datetime.now(UTC).isoformat(),
        )
        self.generations_path.parent.mkdir(parents=True, exist_ok=True)
        with self.generations_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(asdict(record), sort_keys=True) + "\n")
        return record

    def previous(self) -> GenerationSnapshot:
        snapshots = self.snapshots()
        if len(snapshots) < 2:
            raise RuntimeError("No previous generation available")
        return snapshots[-2]

from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from pathlib import Path


@dataclass(frozen=True)
class ExpertRecord:
    name: str
    kind: str
    status: str
    score: float = 0.0
    economic_score: float = 0.0
    validation_score: float = 0.0
    observations: int = 0
    compute_cost: float = 1.0


@dataclass(frozen=True)
class ExpertPoolPolicy:
    max_active_experts: int = 5
    max_total_experts: int = 12
    min_promotion_score: float = 0.55
    prune_below_score: float = 0.20


class ExpertPoolStore:
    def __init__(self, path: str | Path = "artifacts/expert_pool.json") -> None:
        self.path = Path(path)

    def load(self) -> dict[str, ExpertRecord]:
        if not self.path.exists():
            return {}
        payload = json.loads(self.path.read_text(encoding="utf-8"))
        return {name: ExpertRecord(**record) for name, record in payload.items()}

    def save(self, records: dict[str, ExpertRecord]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temp = self.path.with_suffix(".tmp")
        temp.write_text(
            json.dumps({k: asdict(v) for k, v in records.items()}, sort_keys=True),
            encoding="utf-8",
        )
        temp.replace(self.path)

    def upsert(self, record: ExpertRecord) -> None:
        records = self.load()
        records[record.name] = record
        self.save(records)


def compute_budget_weights(
    records: dict[str, ExpertRecord],
    *,
    exploration_floor: float = 0.05,
) -> dict[str, float]:
    active = {
        name: record
        for name, record in records.items()
        if record.status == "active"
    }
    if not active:
        return {}

    raw = {}
    for name, record in active.items():
        quality = max(exploration_floor, record.score)
        efficiency = quality / max(0.1, record.compute_cost)
        raw[name] = efficiency

    total = sum(raw.values())
    return {name: value / total for name, value in raw.items()}


def reconcile_pool(
    records: dict[str, ExpertRecord],
    policy: ExpertPoolPolicy | None = None,
) -> dict[str, ExpertRecord]:
    policy = policy or ExpertPoolPolicy()
    ordered = sorted(
        records.values(),
        key=lambda r: (r.score, r.validation_score, r.economic_score),
        reverse=True,
    )

    result: dict[str, ExpertRecord] = {}
    active_count = 0
    for record in ordered[: policy.max_total_experts]:
        status = record.status
        if record.observations > 0 and record.score < policy.prune_below_score:
            status = "pruned"
        elif (
            status in {"challenger", "sandbox"}
            and record.validation_score >= policy.min_promotion_score
            and active_count < policy.max_active_experts
        ):
            status = "active"

        if status == "active":
            if active_count >= policy.max_active_experts:
                status = "challenger"
            else:
                active_count += 1

        result[record.name] = ExpertRecord(
            name=record.name,
            kind=record.kind,
            status=status,
            score=record.score,
            economic_score=record.economic_score,
            validation_score=record.validation_score,
            observations=record.observations,
            compute_cost=record.compute_cost,
        )

    return result

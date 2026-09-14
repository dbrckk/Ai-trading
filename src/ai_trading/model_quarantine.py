from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass(frozen=True)
class QuarantinePolicy:
    failures_before_quarantine: int = 2
    base_backoff_bars: int = 20
    max_backoff_bars: int = 640


@dataclass(frozen=True)
class QuarantineRecord:
    version: str
    failures: int = 0
    quarantined: bool = False
    next_eligible_bar: int = 0
    last_reason: str = ""


class ModelQuarantineStore:
    def __init__(self, path: str | Path = "artifacts/model_quarantine.json") -> None:
        self.path = Path(path)

    def load(self) -> dict[str, QuarantineRecord]:
        if not self.path.exists():
            return {}
        payload = json.loads(self.path.read_text(encoding="utf-8"))
        return {
            version: QuarantineRecord(**record)
            for version, record in payload.items()
        }

    def save(self, records: dict[str, QuarantineRecord]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temp = self.path.with_suffix(".tmp")
        temp.write_text(
            json.dumps(
                {version: asdict(record) for version, record in records.items()},
                sort_keys=True,
            ),
            encoding="utf-8",
        )
        temp.replace(self.path)

    def record_failure(
        self,
        version: str,
        *,
        processed_bar: int,
        reason: str,
        policy: QuarantinePolicy | None = None,
    ) -> QuarantineRecord:
        policy = policy or QuarantinePolicy()
        records = self.load()
        previous = records.get(version, QuarantineRecord(version=version))
        failures = previous.failures + 1
        exponent = max(0, failures - 1)
        backoff = min(
            policy.max_backoff_bars,
            policy.base_backoff_bars * (2**exponent),
        )
        record = QuarantineRecord(
            version=version,
            failures=failures,
            quarantined=failures >= policy.failures_before_quarantine,
            next_eligible_bar=int(processed_bar + backoff),
            last_reason=reason,
        )
        records[version] = record
        self.save(records)
        return record

    def record_success(self, version: str) -> QuarantineRecord:
        records = self.load()
        record = QuarantineRecord(version=version)
        records[version] = record
        self.save(records)
        return record

    def eligible(self, version: str, *, processed_bar: int) -> bool:
        record = self.load().get(version)
        if record is None:
            return True
        if processed_bar < record.next_eligible_bar:
            return False
        return not record.quarantined

    def release(self, version: str) -> QuarantineRecord:
        records = self.load()
        record = QuarantineRecord(version=version)
        records[version] = record
        self.save(records)
        return record

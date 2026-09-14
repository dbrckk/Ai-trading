from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass
class QualityRecord:
    predictions: list[int]
    confidences: list[float]
    labels: list[int]


class QualityStore:
    def __init__(self, path: str | Path = "artifacts/model_quality.json") -> None:
        self.path = Path(path)

    def load(self) -> dict[str, QualityRecord]:
        if not self.path.exists():
            return {}
        payload = json.loads(self.path.read_text(encoding="utf-8"))
        return {key: QualityRecord(**value) for key, value in payload.items()}

    def save(self, records: dict[str, QualityRecord]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temp = self.path.with_suffix(".tmp")
        temp.write_text(
            json.dumps({k: asdict(v) for k, v in records.items()}, sort_keys=True),
            encoding="utf-8",
        )
        temp.replace(self.path)

    def append(
        self,
        key: str,
        *,
        prediction: int,
        confidence: float,
        label: int,
        maxlen: int = 250,
    ) -> None:
        records = self.load()
        record = records.setdefault(key, QualityRecord([], [], []))
        record.predictions.append(int(prediction))
        record.confidences.append(float(confidence))
        record.labels.append(int(label))
        record.predictions = record.predictions[-maxlen:]
        record.confidences = record.confidences[-maxlen:]
        record.labels = record.labels[-maxlen:]
        self.save(records)

from __future__ import annotations

import json
from dataclasses import asdict, is_dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


class ExperimentRegistry:
    """Append-only JSONL registry for reproducible research runs."""

    def __init__(self, path: str | Path = "artifacts/experiments.jsonl") -> None:
        self.path = Path(path)

    def append(
        self,
        *,
        name: str,
        symbol: str,
        config: dict[str, Any],
        metrics: Any,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        metric_payload = asdict(metrics) if is_dataclass(metrics) else dict(metrics)
        record = {
            "timestamp_utc": datetime.now(UTC).isoformat(),
            "name": name,
            "symbol": symbol,
            "config": config,
            "metrics": metric_payload,
            "metadata": metadata or {},
        }
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, sort_keys=True) + "\n")
        return record

from __future__ import annotations

import json
from collections.abc import Iterable
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd

from .performance import PerformanceMetrics, compute_metrics
from .readiness import ReadinessReport, evaluate_readiness


@dataclass(frozen=True)
class BurnInSnapshot:
    timestamp_utc: str
    equity: float
    scheduler_errors: int
    regimes_covered: int
    bootstrap_probability_positive: float
    processed_bars: int = 0


def calculate_burnin_metrics(
    snapshots: Iterable[BurnInSnapshot],
) -> PerformanceMetrics:
    values = tuple(snapshots)
    if len(values) < 2:
        raise ValueError("Need at least two burn-in snapshots")
    equity = pd.Series([snapshot.equity for snapshot in values], dtype=float)
    return compute_metrics(equity)


class BurnInTracker:
    def __init__(self, path: str | Path = "artifacts/burnin.jsonl") -> None:
        self.path = Path(path)

    def append(
        self,
        *,
        equity: float,
        scheduler_errors: int = 0,
        regimes_covered: int = 0,
        bootstrap_probability_positive: float = 0.0,
        processed_bars: int = 0,
    ) -> BurnInSnapshot:
        if equity <= 0:
            raise ValueError("equity must be positive")
        snapshot = BurnInSnapshot(
            timestamp_utc=datetime.now(UTC).isoformat(),
            equity=float(equity),
            scheduler_errors=int(scheduler_errors),
            regimes_covered=int(regimes_covered),
            bootstrap_probability_positive=float(bootstrap_probability_positive),
            processed_bars=int(processed_bars),
        )
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(asdict(snapshot), sort_keys=True) + "\n")
        return snapshot

    def read(self) -> list[BurnInSnapshot]:
        if not self.path.exists():
            return []
        snapshots: list[BurnInSnapshot] = []
        for line in self.path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                payload = json.loads(line)
                payload.setdefault("processed_bars", len(snapshots) + 1)
                snapshots.append(BurnInSnapshot(**payload))
        return snapshots

    def metrics(self) -> PerformanceMetrics:
        return calculate_burnin_metrics(self.read())

    def readiness(self) -> ReadinessReport:
        snapshots = self.read()
        if len(snapshots) < 2:
            raise ValueError("Need at least two burn-in snapshots")
        latest = snapshots[-1]
        return evaluate_readiness(
            metrics=self.metrics(),
            burn_in_bars=latest.processed_bars or len(snapshots),
            bootstrap_probability_positive=latest.bootstrap_probability_positive,
            regimes_covered=latest.regimes_covered,
            scheduler_errors=latest.scheduler_errors,
        )

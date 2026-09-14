from pathlib import Path

from ai_trading.burnin import BurnInTracker


def test_burnin_tracker_persists_and_computes_metrics(tmp_path: Path) -> None:
    tracker = BurnInTracker(tmp_path / "burnin.jsonl")
    tracker.append(
        equity=100_000.0,
        regimes_covered=3,
        bootstrap_probability_positive=0.8,
    )
    tracker.append(
        equity=101_000.0,
        regimes_covered=3,
        bootstrap_probability_positive=0.8,
    )
    tracker.append(
        equity=102_000.0,
        regimes_covered=3,
        bootstrap_probability_positive=0.8,
    )

    snapshots = tracker.read()
    assert len(snapshots) == 3
    assert tracker.metrics().total_return > 0.0

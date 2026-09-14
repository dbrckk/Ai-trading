import json
from dataclasses import asdict
from datetime import UTC, datetime, timedelta
from pathlib import Path

from ai_trading.lifecycle_log import LifecycleEvent, LifecycleEventLog
from ai_trading.reliability import evaluate_reliability
from ai_trading.resilience import ResilienceState


def transition(
    created_at: datetime,
    from_mode: str,
    to_mode: str,
) -> LifecycleEvent:
    return LifecycleEvent(
        event="resilience_transition",
        version="",
        model_name="",
        reason="",
        failure_type="",
        processed_bar=0,
        artifact_sha256=None,
        artifact_path=None,
        metadata={"from_mode": from_mode, "to_mode": to_mode},
        created_at_utc=created_at.isoformat(),
    )


def write_events(path: Path, events: list[LifecycleEvent]) -> LifecycleEventLog:
    path.write_text(
        "".join(json.dumps(asdict(event), sort_keys=True) + "\n" for event in events),
        encoding="utf-8",
    )
    return LifecycleEventLog(path)


def test_reliability_calculates_state_ratios_and_mttr(tmp_path: Path) -> None:
    start = datetime(2026, 1, 1, tzinfo=UTC)
    log = write_events(
        tmp_path / "lifecycle.jsonl",
        [
            transition(start, "NORMAL", "DEGRADED"),
            transition(start + timedelta(minutes=10), "DEGRADED", "NORMAL"),
            transition(start + timedelta(minutes=50), "NORMAL", "HALT"),
            transition(start + timedelta(minutes=60), "HALT", "NORMAL"),
        ],
    )

    report = evaluate_reliability(
        log,
        ResilienceState(mode="NORMAL"),
        now_utc=start + timedelta(minutes=100),
    )

    assert report.observation_seconds == 6000.0
    assert report.normal_ratio == 0.80
    assert report.degraded_ratio == 0.10
    assert report.halt_ratio == 0.10
    assert report.halt_count == 1
    assert report.incident_count == 2
    assert report.mttr_seconds == 600.0
    assert report.mtbf_seconds == 3000.0
    assert report.reliability_score < 90.0


def test_reliability_is_perfect_without_incidents(tmp_path: Path) -> None:
    report = evaluate_reliability(
        LifecycleEventLog(tmp_path / "lifecycle.jsonl"),
        ResilienceState(mode="NORMAL"),
    )

    assert report.reliability_score == 100.0
    assert report.normal_ratio == 1.0
    assert report.halt_count == 0

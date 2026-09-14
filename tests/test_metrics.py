from pathlib import Path

from ai_trading.crisis_controller import CrisisState
from ai_trading.crisis_state_store import CrisisStateStore
from ai_trading.governor_state_store import GovernorState, GovernorStateStore
from ai_trading.lifecycle_log import LifecycleEventLog
from ai_trading.metrics import collect_metrics, prometheus_text
from ai_trading.model_quarantine import ModelQuarantineStore, QuarantinePolicy
from ai_trading.watchdog import HeartbeatStore


def test_metrics_export_prometheus_text(tmp_path: Path, monkeypatch) -> None:
    governor = GovernorStateStore(tmp_path / "governor.json")
    governor.save(GovernorState(verdict="HALT", reason="x", consecutive_halts=2))
    crisis = CrisisStateStore(tmp_path / "crisis.json")
    crisis.save(CrisisState(mode="defensive"))

    import ai_trading.metrics as metrics_module
    monkeypatch.setattr(
        metrics_module,
        "read_control_plane",
        lambda governor_store=None: type(
            "S",
            (),
            {"governor_verdict": "HALT", "crisis_mode": "defensive"},
        )(),
    )

    snapshot = collect_metrics(
        heartbeat_store=HeartbeatStore(tmp_path / "heartbeat.json"),
        governor_store=governor,
    )
    text = prometheus_text(snapshot)
    assert "ai_trading_governor_halt 1" in text
    assert "ai_trading_crisis_level 2" in text


def test_metrics_include_model_lifecycle_counters(tmp_path: Path, monkeypatch) -> None:
    import ai_trading.metrics as metrics_module

    monkeypatch.setattr(
        metrics_module,
        "read_control_plane",
        lambda governor_store=None: type(
            "S",
            (),
            {"governor_verdict": "TRADE", "crisis_mode": "normal"},
        )(),
    )
    lifecycle = LifecycleEventLog(tmp_path / "lifecycle.jsonl")
    lifecycle.append(event="promotion", version="v2", model_name="ensemble")
    lifecycle.append(
        event="promotion_rejected",
        version="v3",
        model_name="ensemble",
        failure_type="performance_failure",
    )
    lifecycle.append(
        event="rollback",
        version="v2",
        model_name="ensemble",
        failure_type="performance_failure",
    )
    quarantine = ModelQuarantineStore(tmp_path / "quarantine.json")
    quarantine.record_failure(
        "v2",
        processed_bar=10,
        reason="bad",
        policy=QuarantinePolicy(failures_before_quarantine=1),
    )

    snapshot = collect_metrics(
        heartbeat_store=HeartbeatStore(tmp_path / "heartbeat.json"),
        lifecycle_log=lifecycle,
        quarantine_store=quarantine,
    )
    text = prometheus_text(snapshot)

    assert snapshot.promotion_total == 1
    assert snapshot.promotion_rejected_total == 1
    assert snapshot.rollback_total == 1
    assert snapshot.quarantine_total == 1
    assert "ai_trading_rollback_total 1" in text
    assert "ai_trading_quarantine_total 1" in text



def test_metrics_include_recovery_observability(tmp_path: Path, monkeypatch) -> None:
    import ai_trading.metrics as metrics_module

    monkeypatch.setattr(
        metrics_module,
        "read_control_plane",
        lambda governor_store=None: type(
            "S",
            (),
            {"governor_verdict": "TRADE", "crisis_mode": "normal"},
        )(),
    )
    lifecycle = LifecycleEventLog(tmp_path / "lifecycle.jsonl")
    lifecycle.append(
        event="recovery_succeeded",
        version="",
        model_name="",
        metadata={"fallback_depth": 2, "candidates_tested": 3},
    )
    lifecycle.append(
        event="recovery_failed",
        version="",
        model_name="",
        failure_type="technical_failure",
        metadata={"fallback_depth": 4, "candidates_tested": 5},
    )

    snapshot = collect_metrics(
        heartbeat_store=HeartbeatStore(tmp_path / "heartbeat.json"),
        lifecycle_log=lifecycle,
        quarantine_store=ModelQuarantineStore(tmp_path / "quarantine.json"),
    )
    text = prometheus_text(snapshot)

    assert snapshot.recovery_attempt_total == 2
    assert snapshot.recovery_success_total == 1
    assert snapshot.recovery_failure_total == 1
    assert snapshot.recovery_fallback_depth == 4
    assert "ai_trading_recovery_attempt_total 2" in text
    assert "ai_trading_recovery_failure_total 1" in text
    assert "ai_trading_recovery_fallback_depth 4" in text

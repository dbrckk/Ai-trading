from pathlib import Path

from ai_trading.crisis_controller import CrisisState
from ai_trading.crisis_state_store import CrisisStateStore
from ai_trading.governor_state_store import GovernorState, GovernorStateStore
from ai_trading.metrics import collect_metrics, prometheus_text
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

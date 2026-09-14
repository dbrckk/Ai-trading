from pathlib import Path

from ai_trading.readiness_handshake import wait_for_worker_readiness
from ai_trading.watchdog import HeartbeatStore


def test_readiness_handshake_times_out_without_heartbeat(tmp_path: Path) -> None:
    result = wait_for_worker_readiness(
        HeartbeatStore(tmp_path / "heartbeat.json"),
        timeout_seconds=0.02,
        poll_seconds=0.005,
        max_heartbeat_age_seconds=1.0,
    )
    assert not result.ready

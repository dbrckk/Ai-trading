from datetime import UTC, datetime, timedelta
from pathlib import Path

from ai_trading.governor_state_store import GovernorStateStore
from ai_trading.watchdog import Heartbeat, HeartbeatStore, WatchdogPolicy
from ai_trading.watchdog_enforcer import enforce_watchdog


def test_watchdog_enforcer_halts_on_stale_heartbeat(tmp_path: Path) -> None:
    heartbeat_store = HeartbeatStore(tmp_path / "heartbeat.json")
    old = Heartbeat(
        component="multiasset",
        timestamp_utc=(datetime.now(UTC) - timedelta(minutes=10)).isoformat(),
        iteration=1,
        status="ok",
    )
    heartbeat_store.path.write_text(
        '{"component":"multiasset","iteration":1,"status":"ok",'
        f'"timestamp_utc":"{old.timestamp_utc}"}}',
        encoding="utf-8",
    )
    governor = GovernorStateStore(tmp_path / "governor.json")

    result = enforce_watchdog(
        heartbeat_store=heartbeat_store,
        audit_path=tmp_path / "audit.jsonl",
        governor_store=governor,
        policy=WatchdogPolicy(max_heartbeat_age_seconds=30),
    )

    assert result.halted
    assert governor.load().verdict == "HALT"

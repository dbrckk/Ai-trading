from datetime import UTC, datetime, timedelta
from pathlib import Path

from ai_trading.watchdog import (
    Heartbeat,
    HeartbeatStore,
    WatchdogPolicy,
    heartbeat_is_stale,
)


def test_heartbeat_store_and_staleness(tmp_path: Path) -> None:
    store = HeartbeatStore(tmp_path / "heartbeat.json")
    hb = store.write("multiasset", 3)
    assert store.load() == hb
    assert not heartbeat_is_stale(hb, WatchdogPolicy(max_heartbeat_age_seconds=60))

    old = Heartbeat(
        component="multiasset",
        timestamp_utc=(datetime.now(UTC) - timedelta(minutes=10)).isoformat(),
        iteration=1,
        status="ok",
    )
    assert heartbeat_is_stale(old, WatchdogPolicy(max_heartbeat_age_seconds=60))

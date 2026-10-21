from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime

from ai_trading.runtime_status import (
    HostedRuntimeStatus,
    HostedRuntimeStatusStore,
    runtime_status_snapshot,
)


def test_runtime_status_store_round_trip(tmp_path) -> None:
    store = HostedRuntimeStatusStore(tmp_path / "runtime_status.json")
    status = HostedRuntimeStatus(
        engine_status="RUNNING",
        symbol="GC=F",
        interval="5m",
        updated_at_utc="2026-09-15T16:00:00+00:00",
        last_cycle_timestamp="2026-09-15 15:55:00+00:00",
        processed=True,
        side=1,
        confidence=0.73,
        approved=True,
        reason="approved",
        equity=100_250.0,
        units=2.0,
        processed_bars=12,
        cycle_duration_seconds=14.2,
        mtf_evaluated=True,
    )

    store.save(status)

    assert store.load() == status

    # 15m cron permits a longer RUNNING heartbeat, never an indefinitely
    # STARTING paper cycle with no completed scheduler delivery.
    current = datetime(2026, 9, 15, 16, 5, 1, tzinfo=UTC)
    starting = replace(status, engine_status="STARTING", poll_seconds=900.0)
    blocked = runtime_status_snapshot(starting, now=current)
    assert blocked["engine_status"] == "STALE"
    assert blocked["heartbeat_stale_after_seconds"] == 300.0
    assert blocked["engine_healthy"] is False

    running = runtime_status_snapshot(
        replace(starting, engine_status="RUNNING"),
        now=current,
    )
    assert running["engine_status"] == "RUNNING"
    assert running["heartbeat_stale_after_seconds"] == 2700.0
    assert running["engine_healthy"] is True

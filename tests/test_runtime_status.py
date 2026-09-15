from __future__ import annotations

from ai_trading.runtime_status import HostedRuntimeStatus, HostedRuntimeStatusStore


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
    )

    store.save(status)

    assert store.load() == status

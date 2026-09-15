from __future__ import annotations

from ai_trading.dashboard import render_dashboard
from ai_trading.runtime_state import RuntimeStateStore
from ai_trading.runtime_status import HostedRuntimeStatus, HostedRuntimeStatusStore
from ai_trading.trade_journal import TradeJournal


def test_dashboard_shows_engine_and_latest_decision(tmp_path) -> None:
    journal = TradeJournal(tmp_path / "trades.jsonl")
    state_store = RuntimeStateStore(tmp_path / "runtime_state.json")
    status_store = HostedRuntimeStatusStore(tmp_path / "runtime_status.json")
    status_store.save(
        HostedRuntimeStatus(
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
    )

    page = render_dashboard(
        journal,
        state_store,
        100_000.0,
        runtime_status_store=status_store,
    )

    assert "RUNNING" in page
    assert "GC=F · 5m" in page
    assert "LONG" in page
    assert "73.0%" in page
    assert "APPROVED" in page
    assert "2026-09-15 15:55:00+00:00" in page

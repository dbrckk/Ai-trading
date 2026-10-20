from __future__ import annotations

from datetime import UTC, datetime

from ai_trading.dashboard import render_dashboard
from ai_trading.runtime_state import RuntimeStateStore
from ai_trading.runtime_status import HostedRuntimeStatus, HostedRuntimeStatusStore
from ai_trading.trade_journal import TradeJournal


def test_dashboard_hides_expired_paper_decision(tmp_path) -> None:
    # Fixed open Gold session: wall-clock maintenance windows must not alter the assertion.
    now = datetime(2026, 9, 15, 19, 30, tzinfo=UTC)
    journal = TradeJournal(tmp_path / "trades.jsonl")
    state_store = RuntimeStateStore(tmp_path / "runtime_state.json")
    status_store = HostedRuntimeStatusStore(tmp_path / "runtime_status.json")
    status_store.save(
        HostedRuntimeStatus(
            engine_status="RUNNING",
            symbol="GC=F",
            interval="5m",
            updated_at_utc=now.isoformat(),
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
        now=now,
    )

    assert "RUNNING" in page
    assert "GC=F · 5m" in page
    assert "LONG" not in page
    assert "73.0%" not in page
    assert "Paper signal status: DELAYED" in page
    assert "2026-09-15 15:55:00+00:00" in page

from datetime import UTC, datetime

from ai_trading.market_freshness import (
    classify_market_freshness,
    market_session_open,
)
from ai_trading.runtime_status import HostedRuntimeStatus


def _status(
    *,
    engine_status: str = "RUNNING",
    reason: str = "processed 1 bar(s)",
    error: str | None = None,
) -> HostedRuntimeStatus:
    return HostedRuntimeStatus(
        engine_status=engine_status,
        symbol="GC=F",
        interval="5m",
        updated_at_utc="2026-09-21T12:00:00+00:00",
        reason=reason,
        error=error,
        poll_seconds=300.0,
    )


def test_btc_session_is_always_open() -> None:
    saturday = datetime(2026, 9, 19, 12, 0, tzinfo=UTC)

    assert market_session_open("BTC-USD", now=saturday) is True


def test_dax_regular_weekday_session_is_dst_aware() -> None:
    opening = datetime(2026, 9, 21, 7, 0, tzinfo=UTC)
    after_close = datetime(2026, 9, 21, 16, 0, tzinfo=UTC)

    assert market_session_open("^GDAXI", now=opening) is True
    assert market_session_open("^GDAXI", now=after_close) is False


def test_gold_daily_maintenance_window_is_closed() -> None:
    maintenance = datetime(2026, 9, 21, 21, 30, tzinfo=UTC)
    reopened = datetime(2026, 9, 21, 22, 30, tzinfo=UTC)

    assert market_session_open("GC=F", now=maintenance) is False
    assert market_session_open("GC=F", now=reopened) is True


def test_gold_weekend_is_closed() -> None:
    saturday = datetime(2026, 9, 19, 12, 0, tzinfo=UTC)

    assert market_session_open("GC=F", now=saturday) is False


def test_catch_up_takes_priority_over_live_state() -> None:
    status = _status(reason="catch-up pending")

    freshness, session_open = classify_market_freshness(
        "GC=F",
        status,
        {"engine_status": "RUNNING"},
        now=datetime(2026, 9, 21, 12, 0, tzinfo=UTC),
    )

    assert freshness == "CATCHING_UP"
    assert session_open is True


def test_known_data_gap_is_exposed_as_provider_gap_while_market_open() -> None:
    status = _status(
        engine_status="ERROR",
        error="RuntimeError: persisted_bar_outside_loaded_history",
    )

    freshness, session_open = classify_market_freshness(
        "^GDAXI",
        status,
        {"engine_status": "ERROR"},
        now=datetime(2026, 9, 21, 12, 0, tzinfo=UTC),
    )

    assert freshness == "PROVIDER_GAP"
    assert session_open is True


def test_closed_session_is_not_misreported_as_delayed() -> None:
    status = _status()

    freshness, session_open = classify_market_freshness(
        "^GDAXI",
        status,
        {"engine_status": "STALE"},
        now=datetime(2026, 9, 20, 12, 0, tzinfo=UTC),
    )

    assert freshness == "MARKET_CLOSED"
    assert session_open is False


def test_stale_heartbeat_during_open_session_is_delayed() -> None:
    status = _status()

    freshness, session_open = classify_market_freshness(
        "^GDAXI",
        status,
        {"engine_status": "STALE"},
        now=datetime(2026, 9, 21, 12, 0, tzinfo=UTC),
    )

    assert freshness == "DELAYED"
    assert session_open is True

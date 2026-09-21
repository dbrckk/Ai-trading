from __future__ import annotations

from datetime import UTC, datetime, time
from .runtime_status import HostedRuntimeStatus


_PROVIDER_GAP_ERRORS = {
    "RuntimeError: persisted_bar_outside_loaded_history",
    "RuntimeError: no_eligible_market_bar",
}


def _utc_now(now: datetime | None) -> datetime:
    current = now or datetime.now(UTC)
    if current.tzinfo is None:
        return current.replace(tzinfo=UTC)
    return current.astimezone(UTC)


def market_session_open(symbol: str, *, now: datetime | None = None) -> bool | None:
    from zoneinfo import ZoneInfo

    """Return the expected weekly session state for supported paper markets.

    This intentionally models regular weekly sessions only. Exchange holidays are
    not guessed; unsupported symbols return None instead of a false precision.
    """

    current = _utc_now(now)

    if symbol == "BTC-USD":
        return True

    if symbol == "^GDAXI":
        local = current.astimezone(ZoneInfo("Europe/Berlin"))
        if local.weekday() >= 5:
            return False
        return time(9, 0) <= local.time().replace(tzinfo=None) < time(17, 30)

    if symbol == "GC=F":
        local = current.astimezone(ZoneInfo("America/New_York"))
        weekday = local.weekday()
        local_time = local.time().replace(tzinfo=None)

        if weekday == 5:
            return False
        if weekday == 6:
            return local_time >= time(18, 0)
        if weekday == 4:
            return local_time < time(17, 0)
        return not (time(17, 0) <= local_time < time(18, 0))

    return None


def classify_market_freshness(
    symbol: str,
    status: HostedRuntimeStatus | None,
    status_snapshot: dict[str, object],
    *,
    now: datetime | None = None,
) -> tuple[str, bool | None]:
    session_open = market_session_open(symbol, now=now)
    if status is None:
        return "OFF", session_open

    engine_status = str(status_snapshot.get("engine_status") or "OFF").upper()

    if status.reason == "catch-up pending" and engine_status in {
        "RUNNING",
        "STARTING",
        "STALE",
    }:
        return "CATCHING_UP", session_open

    if engine_status == "ERROR":
        if session_open is True and status.error in _PROVIDER_GAP_ERRORS:
            return "PROVIDER_GAP", session_open
        return "ERROR", session_open

    if session_open is False and engine_status in {"RUNNING", "STARTING", "STALE"}:
        return "MARKET_CLOSED", session_open

    if engine_status == "STALE":
        return "DELAYED", session_open
    if engine_status == "STARTING":
        return "STARTING", session_open
    if engine_status == "RUNNING":
        return "LIVE", session_open
    return engine_status, session_open

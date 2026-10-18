from __future__ import annotations

from datetime import UTC, datetime, time
from math import isfinite
from re import fullmatch

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
    """Return the expected weekly session state for supported paper markets.

    This intentionally models regular weekly sessions only. Exchange holidays are
    not guessed; unsupported symbols return None instead of a false precision.
    """

    from zoneinfo import ZoneInfo

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


def paper_signal_snapshot(
    status: HostedRuntimeStatus | None,
    *,
    freshness: str,
    session_open: bool | None,
    now: datetime | None = None,
) -> dict[str, object]:
    """Only expose a fresh, completed PAPER decision; never imply live trade advice."""
    snapshot: dict[str, object] = {
        "signal": None,
        "confidence": None,
        "risk_approved": None,
        "signal_state": "WAITING",
        "signal_time": status.last_cycle_timestamp if status is not None else None,
        "signal_age_seconds": None,
        "decision_reason": status.decision_reason if status is not None else None,
    }
    if status is None or not status.processed:
        return snapshot
    if freshness != "LIVE" or session_open is not True or status.error:
        snapshot["signal_state"] = "UNAVAILABLE"
        return snapshot

    units = {"m": 60, "h": 3600, "d": 86400}
    match = fullmatch(r"([1-9][0-9]*)(m|h|d)", status.interval)
    if match is None or not status.last_cycle_timestamp:
        snapshot["signal_state"] = "UNVERIFIED"
        return snapshot
    try:
        timestamp = datetime.fromisoformat(status.last_cycle_timestamp)
    except ValueError:
        snapshot["signal_state"] = "UNVERIFIED"
        return snapshot
    if timestamp.tzinfo is None:
        snapshot["signal_state"] = "UNVERIFIED"
        return snapshot

    age_seconds = (_utc_now(now) - timestamp.astimezone(UTC)).total_seconds()
    snapshot["signal_age_seconds"] = max(0.0, age_seconds)
    max_age = max(3 * int(match.group(1)) * units[match.group(2)], 300)
    if not -60.0 <= age_seconds <= max_age:
        snapshot["signal_state"] = "DELAYED"
        return snapshot
    if status.side not in (-1, 0, 1) or not isfinite(status.confidence):
        snapshot["signal_state"] = "UNVERIFIED"
        return snapshot
    if not 0.0 <= status.confidence <= 1.0:
        snapshot["signal_state"] = "UNVERIFIED"
        return snapshot
    snapshot["signal"] = {1: "LONG", -1: "SHORT", 0: "FLAT"}[status.side]
    snapshot["confidence"] = status.confidence
    snapshot["risk_approved"] = bool(status.approved)
    snapshot["signal_state"] = (
        "NO_TRADE" if status.side == 0
        else "PAPER_APPROVED" if status.approved
        else "RISK_REJECTED"
    )
    return snapshot

from __future__ import annotations

import hmac
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime

from .paper_cycle import PaperCycleResult
from .paper_cycle_service import PaperCycleServiceError
from .persistence import SchedulerDelivery


@dataclass(frozen=True)
class SchedulerHttpResponse:
    status_code: int
    payload: dict[str, object]


_ALLOWED_SCHEDULER_SOURCES = {"cloudflare"}
_SCHEDULER_FRESHNESS_SECONDS = 12 * 60


def scheduler_telemetry_payload(
    response: SchedulerHttpResponse,
    source: str | None,
) -> dict[str, object]:
    normalized_source = (source or "").strip().lower()
    if normalized_source not in _ALLOWED_SCHEDULER_SOURCES:
        normalized_source = "external"

    payload: dict[str, object] = {
        "event": "scheduler_request",
        "source": normalized_source,
        "status_code": response.status_code,
        "ok": response.payload.get("ok") is True,
    }
    processed = response.payload.get("processed")
    if isinstance(processed, int) and not isinstance(processed, bool):
        payload["processed"] = processed
    return payload


def _utc_now(now: datetime | None) -> datetime:
    current = now or datetime.now(UTC)
    if current.tzinfo is None:
        return current.replace(tzinfo=UTC)
    return current.astimezone(UTC)


def _delivery_age_seconds(
    timestamp_utc: str,
    *,
    now: datetime,
) -> float | None:
    try:
        timestamp = datetime.fromisoformat(timestamp_utc.replace("Z", "+00:00"))
    except ValueError:
        return None
    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=UTC)
    else:
        timestamp = timestamp.astimezone(UTC)
    age = (now - timestamp).total_seconds()
    if age < -60.0:
        return None
    return max(0.0, age)


def scheduler_delivery_overview(
    deliveries: tuple[SchedulerDelivery, ...],
    *,
    now: datetime | None = None,
    freshness_seconds: float = _SCHEDULER_FRESHNESS_SECONDS,
) -> dict[str, object]:
    if freshness_seconds <= 0:
        raise ValueError("freshness_seconds must be positive")

    consecutive_cloudflare_successes = 0
    for delivery in reversed(deliveries):
        if (
            delivery.source == "cloudflare"
            and delivery.ok
            and delivery.status_code == 200
        ):
            consecutive_cloudflare_successes += 1
            continue
        break

    latest = deliveries[-1] if deliveries else None
    current = _utc_now(now)
    latest_age_seconds = (
        None
        if latest is None
        else _delivery_age_seconds(latest.timestamp_utc, now=current)
    )
    cloudflare_delivery_fresh = bool(
        latest is not None
        and latest.source == "cloudflare"
        and latest.ok
        and latest.status_code == 200
        and latest_age_seconds is not None
        and latest_age_seconds <= freshness_seconds
    )
    return {
        "delivery_count": len(deliveries),
        "consecutive_cloudflare_successes": consecutive_cloudflare_successes,
        "cloudflare_delivery_fresh": cloudflare_delivery_fresh,
        "cloudflare_delivery_verified": (
            consecutive_cloudflare_successes >= 3
            and cloudflare_delivery_fresh
        ),
        "freshness_seconds": float(freshness_seconds),
        "last_delivery_age_seconds": latest_age_seconds,
        "last_delivery_timestamp_utc": None if latest is None else latest.timestamp_utc,
        "last_source": None if latest is None else latest.source,
        "last_status_code": None if latest is None else latest.status_code,
        "deliveries": [
            {
                "timestamp_utc": delivery.timestamp_utc,
                "source": delivery.source,
                "status_code": delivery.status_code,
                "ok": delivery.ok,
                "processed": delivery.processed,
            }
            for delivery in deliveries
        ],
    }


def _authorized(authorization: str | None, configured_token: str) -> bool:
    if authorization is None or not authorization.startswith("Bearer "):
        return False
    provided = authorization.removeprefix("Bearer ")
    if not provided:
        return False
    return hmac.compare_digest(provided.encode(), configured_token.encode())


def handle_scheduler_request(
    *,
    authorization: str | None,
    configured_token: str,
    run_cycle: Callable[[], PaperCycleResult],
) -> SchedulerHttpResponse:
    if not configured_token:
        return SchedulerHttpResponse(
            status_code=503,
            payload={"ok": False, "error": "scheduler unavailable"},
        )
    if not _authorized(authorization, configured_token):
        return SchedulerHttpResponse(
            status_code=401,
            payload={"ok": False, "error": "unauthorized"},
        )

    try:
        result = run_cycle()
    except PaperCycleServiceError as exc:
        if exc.code == "storage_unavailable":
            return SchedulerHttpResponse(
                status_code=503,
                payload={"ok": False, "error": "storage unavailable"},
            )
        return SchedulerHttpResponse(
            status_code=500,
            payload={"ok": False, "error": "worker failure"},
        )

    return SchedulerHttpResponse(
        status_code=200,
        payload={
            "ok": True,
            "processed": int(result.processed),
            "status": "RUNNING",
        },
    )

from __future__ import annotations

import hmac
from collections.abc import Callable
from dataclasses import dataclass

from .paper_cycle import PaperCycleResult
from .paper_cycle_service import PaperCycleServiceError


@dataclass(frozen=True)
class SchedulerHttpResponse:
    status_code: int
    payload: dict[str, object]


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

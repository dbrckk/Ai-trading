from __future__ import annotations

from ai_trading.paper_cycle import PaperCycleResult
from ai_trading.paper_cycle_service import PaperCycleServiceError
from ai_trading.scheduler_endpoint import handle_scheduler_request


def successful_result(
    *,
    processed: int = 0,
    reason: str = "no new eligible bar",
) -> PaperCycleResult:
    return PaperCycleResult(
        processed=processed,
        remaining_backlog=False,
        last_processed="2026-09-16 08:00:00+00:00",
        processed_bars=max(1, processed),
        reason=reason,
    )


def test_missing_server_token_fails_closed() -> None:
    calls = 0

    def run_cycle() -> PaperCycleResult:
        nonlocal calls
        calls += 1
        return successful_result()

    response = handle_scheduler_request(
        authorization="Bearer supplied",
        configured_token="",
        run_cycle=run_cycle,
    )

    assert calls == 0
    assert response.status_code == 503
    assert response.payload == {"ok": False, "error": "scheduler unavailable"}


def test_missing_authorization_is_unauthorized() -> None:
    response = handle_scheduler_request(
        authorization=None,
        configured_token="expected-token",
        run_cycle=lambda: successful_result(),
    )

    assert response.status_code == 401
    assert response.payload == {"ok": False, "error": "unauthorized"}


def test_wrong_scheme_is_unauthorized() -> None:
    response = handle_scheduler_request(
        authorization="Basic expected-token",
        configured_token="expected-token",
        run_cycle=lambda: successful_result(),
    )

    assert response.status_code == 401
    assert response.payload == {"ok": False, "error": "unauthorized"}


def test_wrong_bearer_token_is_unauthorized() -> None:
    response = handle_scheduler_request(
        authorization="Bearer wrong-token",
        configured_token="expected-token",
        run_cycle=lambda: successful_result(),
    )

    assert response.status_code == 401
    assert response.payload == {"ok": False, "error": "unauthorized"}


def test_valid_token_runs_exactly_one_cycle() -> None:
    calls = 0

    def run_cycle() -> PaperCycleResult:
        nonlocal calls
        calls += 1
        return successful_result(processed=2, reason="processed 2 bar(s)")

    response = handle_scheduler_request(
        authorization="Bearer expected-token",
        configured_token="expected-token",
        run_cycle=run_cycle,
    )

    assert calls == 1
    assert response.status_code == 200
    assert response.payload == {"ok": True, "processed": 2, "status": "RUNNING"}


def test_concurrent_progress_is_successful_noop() -> None:
    response = handle_scheduler_request(
        authorization="Bearer expected-token",
        configured_token="expected-token",
        run_cycle=lambda: successful_result(
            processed=0,
            reason="concurrent progress observed",
        ),
    )

    assert response.status_code == 200
    assert response.payload == {"ok": True, "processed": 0, "status": "RUNNING"}


def test_storage_failure_is_sanitized() -> None:
    def run_cycle() -> PaperCycleResult:
        raise PaperCycleServiceError(
            code="storage_unavailable",
            error_type="OperationalError",
        )

    response = handle_scheduler_request(
        authorization="Bearer expected-token",
        configured_token="expected-token",
        run_cycle=run_cycle,
    )

    assert response.status_code == 503
    assert response.payload == {"ok": False, "error": "storage unavailable"}
    rendered = repr(response.payload)
    assert "OperationalError" not in rendered
    assert "expected-token" not in rendered
    assert "postgresql://" not in rendered


def test_execution_failure_is_sanitized() -> None:
    def run_cycle() -> PaperCycleResult:
        raise PaperCycleServiceError(
            code="execution_failed",
            error_type="RuntimeError",
        )

    response = handle_scheduler_request(
        authorization="Bearer expected-token",
        configured_token="expected-token",
        run_cycle=run_cycle,
    )

    assert response.status_code == 500
    assert response.payload == {"ok": False, "error": "worker failure"}
    rendered = repr(response.payload)
    assert "RuntimeError" not in rendered
    assert "expected-token" not in rendered
    assert "postgresql://" not in rendered

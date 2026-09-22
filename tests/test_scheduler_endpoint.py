from __future__ import annotations

import json
import socket
import time
from datetime import UTC, datetime, timedelta
from threading import Thread
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import pytest

from ai_trading.dashboard import serve_dashboard
from ai_trading.paper_cycle import PaperCycleResult
from ai_trading.paper_cycle_service import PaperCycleServiceError
from ai_trading.persistence import SchedulerDelivery
from ai_trading.scheduler_endpoint import (
    SchedulerHttpResponse,
    handle_scheduler_request,
    scheduler_delivery_overview,
    scheduler_telemetry_payload,
)


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


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _request(
    url: str,
    *,
    method: str = "GET",
    headers: dict[str, str] | None = None,
    body: bytes | None = None,
) -> tuple[int, str]:
    request = Request(url, method=method, headers=headers or {}, data=body)
    try:
        with urlopen(request, timeout=2) as response:
            return response.status, response.read().decode()
    except HTTPError as exc:
        return exc.code, exc.read().decode()


def _start_scheduler_dashboard(
    tmp_path,
    *,
    scheduler_token: str,
    paper_cycle_executor,
) -> int:
    port = _free_port()
    thread = Thread(
        target=serve_dashboard,
        kwargs={
            "journal_path": tmp_path / "trades.jsonl",
            "host": "127.0.0.1",
            "port": port,
            "state_path": tmp_path / "runtime_state.json",
            "status_path": tmp_path / "runtime_status.json",
            "scheduler_token": scheduler_token,
            "paper_cycle_executor": paper_cycle_executor,
        },
        daemon=True,
    )
    thread.start()
    deadline = time.time() + 1.0
    while time.time() < deadline:
        try:
            status, _ = _request(f"http://127.0.0.1:{port}/")
            if status == 200:
                return port
        except URLError:
            time.sleep(0.02)
    raise AssertionError("dashboard server did not start")


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


def test_http_scheduler_rejects_missing_and_wrong_authorization(tmp_path) -> None:
    port = _start_scheduler_dashboard(
        tmp_path,
        scheduler_token="server-secret",
        paper_cycle_executor=lambda: successful_result(),
    )
    url = f"http://127.0.0.1:{port}/internal/paper-cycle"

    missing_status, missing_body = _request(url, method="POST")
    wrong_status, wrong_body = _request(
        url,
        method="POST",
        headers={"Authorization": "Bearer wrong-secret"},
    )

    assert missing_status == 401
    assert json.loads(missing_body) == {"ok": False, "error": "unauthorized"}
    assert wrong_status == 401
    assert json.loads(wrong_body) == {"ok": False, "error": "unauthorized"}


def test_http_scheduler_valid_token_runs_one_cycle_and_ignores_body(tmp_path) -> None:
    calls = 0

    def fake_cycle() -> PaperCycleResult:
        nonlocal calls
        calls += 1
        return successful_result(processed=1, reason="processed 1 bar(s)")

    port = _start_scheduler_dashboard(
        tmp_path,
        scheduler_token="server-secret",
        paper_cycle_executor=fake_cycle,
    )
    status, body = _request(
        f"http://127.0.0.1:{port}/internal/paper-cycle?symbol=SI%3DF&interval=1m",
        method="POST",
        headers={
            "Authorization": "Bearer server-secret",
            "Content-Type": "application/json",
        },
        body=b'{"symbol":"SI=F","interval":"1m"}',
    )

    assert status == 200
    assert calls == 1
    assert json.loads(body) == {"ok": True, "processed": 1, "status": "RUNNING"}


def test_http_scheduler_other_post_routes_are_not_exposed(tmp_path) -> None:
    port = _start_scheduler_dashboard(
        tmp_path,
        scheduler_token="server-secret",
        paper_cycle_executor=lambda: successful_result(),
    )

    status, _ = _request(
        f"http://127.0.0.1:{port}/api/status",
        method="POST",
        headers={"Authorization": "Bearer server-secret"},
    )

    assert status == 404


def test_http_scheduler_failure_response_never_leaks_secrets(tmp_path) -> None:
    def fail_cycle() -> PaperCycleResult:
        raise PaperCycleServiceError(
            code="execution_failed",
            error_type="postgresql://user:password@example.invalid/private",
        )

    port = _start_scheduler_dashboard(
        tmp_path,
        scheduler_token="server-secret",
        paper_cycle_executor=fail_cycle,
    )
    status, body = _request(
        f"http://127.0.0.1:{port}/internal/paper-cycle",
        method="POST",
        headers={"Authorization": "Bearer server-secret"},
    )

    assert status == 500
    assert json.loads(body) == {"ok": False, "error": "worker failure"}
    assert "server-secret" not in body
    assert "postgresql://" not in body
    assert "example.invalid" not in body


def test_scheduler_telemetry_is_sanitized_and_identifies_cloudflare() -> None:
    response = SchedulerHttpResponse(
        status_code=200,
        payload={"ok": True, "processed": 3, "status": "RUNNING"},
    )

    payload = scheduler_telemetry_payload(response, "cloudflare")

    assert payload == {
        "event": "scheduler_request",
        "source": "cloudflare",
        "status_code": 200,
        "ok": True,
        "processed": 3,
    }
    assert "Authorization" not in repr(payload)
    assert "token" not in repr(payload).lower()


def test_scheduler_telemetry_does_not_trust_arbitrary_source_headers() -> None:
    response = SchedulerHttpResponse(
        status_code=401,
        payload={"ok": False, "error": "unauthorized"},
    )

    payload = scheduler_telemetry_payload(
        response,
        "cloudflare token=super-secret",
    )

    assert payload == {
        "event": "scheduler_request",
        "source": "external",
        "status_code": 401,
        "ok": False,
    }
    assert "super-secret" not in repr(payload)


def test_scheduler_delivery_overview_verifies_three_consecutive_cloudflare_successes() -> None:
    deliveries = tuple(
        SchedulerDelivery(
            timestamp_utc=f"2026-09-21T16:{minute:02d}:00+00:00",
            source="cloudflare",
            status_code=200,
            ok=True,
            processed=1,
        )
        for minute in (0, 5, 10)
    )

    overview = scheduler_delivery_overview(
        deliveries,
        now=datetime(2026, 9, 21, 16, 10, tzinfo=UTC),
    )

    assert overview["consecutive_cloudflare_successes"] == 3
    assert overview["cloudflare_delivery_fresh"] is True
    assert overview["cloudflare_delivery_verified"] is True
    assert overview["last_delivery_age_seconds"] == 0.0
    assert overview["last_source"] == "cloudflare"


def test_http_scheduler_exposes_durable_cloudflare_delivery_evidence(tmp_path) -> None:
    port = _start_scheduler_dashboard(
        tmp_path,
        scheduler_token="server-secret",
        paper_cycle_executor=lambda: successful_result(processed=1),
    )
    url = f"http://127.0.0.1:{port}/internal/paper-cycle"
    for _ in range(3):
        status, body = _request(
            url,
            method="POST",
            headers={
                "Authorization": "Bearer server-secret",
                "X-Scheduler-Source": "cloudflare",
            },
        )
        assert status == 200
        assert json.loads(body)["ok"] is True

    status, body = _request(f"http://127.0.0.1:{port}/api/scheduler")
    payload = json.loads(body)

    assert status == 200
    assert payload["delivery_count"] == 3
    assert payload["consecutive_cloudflare_successes"] == 3
    assert payload["cloudflare_delivery_verified"] is True
    assert all(item["source"] == "cloudflare" for item in payload["deliveries"])
    assert "server-secret" not in body



def test_scheduler_delivery_verification_expires_when_latest_success_is_stale() -> None:
    now = datetime(2026, 9, 21, 17, 0, tzinfo=UTC)
    deliveries = tuple(
        SchedulerDelivery(
            timestamp_utc=(now - timedelta(minutes=offset)).isoformat(),
            source="cloudflare",
            status_code=200,
            ok=True,
            processed=1,
        )
        for offset in (25, 20, 15)
    )

    overview = scheduler_delivery_overview(deliveries, now=now)

    assert overview["consecutive_cloudflare_successes"] == 3
    assert overview["cloudflare_delivery_fresh"] is False
    assert overview["cloudflare_delivery_verified"] is False
    assert overview["last_delivery_age_seconds"] == 15 * 60


def test_scheduler_delivery_overview_rejects_invalid_freshness_window() -> None:
    with pytest.raises(ValueError, match="freshness_seconds"):
        scheduler_delivery_overview((), freshness_seconds=0)



from __future__ import annotations

import json
import socket
import time
from threading import Thread
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from ai_trading.dashboard import serve_dashboard
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

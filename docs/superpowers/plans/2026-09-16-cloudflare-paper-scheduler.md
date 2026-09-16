# Cloudflare Paper Scheduler Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the unreliable automatic GitHub Actions trigger with a free Cloudflare Cron Trigger that securely wakes Render every five minutes, while preserving the existing paper-only execution path, Neon durability, bounded catch-up, and GitHub manual fallback.

**Architecture:** Move the existing CLI orchestration into one shared Python service. Both the CLI and a new authenticated `POST /internal/paper-cycle` Render endpoint call that service. A minimal Cloudflare Worker sends only an authenticated POST every five minutes. Neon remains the only durable runtime store. The first implementation PR keeps the existing GitHub `schedule:` block. Only after a real Cloudflare scheduled heartbeat is proven does a second PR remove GitHub automatic scheduling and retain `workflow_dispatch` only.

**Tech Stack:** Python 3.11+, stdlib `http.server`, Typer, psycopg 3, River/joblib, PostgreSQL 16-compatible Neon, Render Free, Cloudflare Workers Cron, Node.js 22 built-in test runner, GitHub Actions, pytest, Ruff.

**Spec:** `docs/superpowers/specs/2026-09-16-cloudflare-paper-scheduler-design.md`

## Global Constraints

- Paper trading only. Never add live broker routing, live broker credentials, or a real-order path.
- Production runtime key remains `paper:GC=F:5m:online-river:v1` via `build_runtime_key()`.
- HTTP callers cannot select symbol, period, interval, catch-up limit, strategy, or risk settings.
- Production settings remain `GC=F`, `5d`, `5m`, maximum 12 catch-up bars, status poll interval 300 seconds.
- `AI_TRADING_DATABASE_URL` remains the production DB selector; configured DB failure is fail-closed with no file fallback.
- Render remains `AI_TRADING_EXTERNAL_SCHEDULER=1`; its embedded daemon stays disabled.
- Scheduler token is independent of DB/GitHub/Render/Cloudflare account credentials.
- Never commit, log, return, or place in issue/PR text any scheduler token, DB URL, DB host, or raw provider exception.
- Cloudflare contains no trading/model/data logic and no Neon credential.
- Delivery is at-least-once. Durable `last_processed` and PostgreSQL revision CAS remain the correctness boundary.
- Benign CAS loss is a successful logical no-op, not an HTTP error.
- First implementation PR must not remove GitHub `schedule:`.
- Remove GitHub automatic scheduling only after a real Cloudflare scheduled heartbeat is observed.
- Close issue #19 only after another Cloudflare scheduled heartbeat is observed after GitHub cutover.
- Do not delete the temporary Render PostgreSQL instance without explicit user approval.

---

## Task 1: Shared Production Paper-Cycle Service

**Files**
- Create: `src/ai_trading/paper_cycle_service.py`
- Create: `tests/test_paper_cycle_service.py`
- Modify: `src/ai_trading/command_app.py`
- Modify: `tests/test_paper_cycle_cli.py`

### Step 1.1 — RED: write the service tests

Create `tests/test_paper_cycle_service.py` with these concrete helpers:

```python
from __future__ import annotations

import pytest

from ai_trading.paper_cycle import PaperCycleResult
from ai_trading.paper_cycle_service import (
    PaperCycleServiceError,
    ProductionPaperCycleSettings,
    run_production_paper_cycle,
)
from ai_trading.persistence import PersistedRuntime
from ai_trading.runtime_state import RuntimeState
from ai_trading.runtime_status import HostedRuntimeStatus


class FakePersistence:
    def __init__(self) -> None:
        self.statuses: list[HostedRuntimeStatus] = []
        self.state = RuntimeState(
            cash=99_500.0,
            units=2.0,
            last_price=101.0,
            peak_equity=100_000.0,
            day_start_equity=100_000.0,
            last_processed="2026-09-16 08:00:00+00:00",
            processed_bars=4,
            last_learning_cycle_bar=0,
        )

    def save_runtime_status(self, runtime_key: str, status: HostedRuntimeStatus) -> None:
        assert runtime_key == "paper:GC=F:5m:online-river:v1"
        self.statuses.append(status)

    def load_runtime(self, runtime_key: str, starting_cash: float) -> PersistedRuntime:
        assert runtime_key == "paper:GC=F:5m:online-river:v1"
        assert starting_cash == 100_000.0
        return PersistedRuntime(state=self.state, model=None, revision=4, is_new=False)


class FakeRunner:
    def __init__(self, persistence: FakePersistence) -> None:
        self.persistence = persistence

    def run_once(
        self,
        *,
        symbol: str,
        period: str,
        interval: str,
        max_catchup_bars: int,
    ) -> PaperCycleResult:
        assert (symbol, period, interval, max_catchup_bars) == ("GC=F", "5d", "5m", 12)
        return PaperCycleResult(
            processed=2,
            remaining_backlog=False,
            last_processed="2026-09-16 08:00:00+00:00",
            processed_bars=4,
            reason="processed 2 bar(s)",
        )
```

Add these tests:

```python
def test_service_persists_starting_and_running_status() -> None:
    backend = FakePersistence()
    result = run_production_paper_cycle(
        ProductionPaperCycleSettings(),
        persistence=backend,
        runner_factory=lambda persistence: FakeRunner(persistence),
    )

    assert result.processed == 2
    assert [status.engine_status for status in backend.statuses] == ["STARTING", "RUNNING"]
    final = backend.statuses[-1]
    assert final.symbol == "GC=F"
    assert final.interval == "5m"
    assert final.poll_seconds == 300.0
    assert final.processed is True
    assert final.processed_bars == 4
    assert final.units == 2.0
    assert final.equity == 99_702.0
    assert final.reason == "processed 2 bar(s)"


def test_persistence_factory_failure_is_sanitized() -> None:
    def broken_factory():
        raise RuntimeError("postgresql://user:secret@example.invalid/private")

    with pytest.raises(PaperCycleServiceError) as caught:
        run_production_paper_cycle(
            ProductionPaperCycleSettings(),
            persistence_factory=broken_factory,
        )

    error = caught.value
    assert error.code == "storage_unavailable"
    assert error.error_type == "RuntimeError"
    assert error.__cause__ is None
    assert "postgresql://" not in str(error)
    assert "secret" not in repr(error)
    assert "example.invalid" not in repr(error)


def test_starting_status_failure_never_runs_worker() -> None:
    backend = FakePersistence()
    calls = 0

    def broken_save(runtime_key, status):
        del runtime_key, status
        raise RuntimeError("storage down")

    backend.save_runtime_status = broken_save

    def runner_factory(persistence):
        nonlocal calls
        del persistence
        calls += 1
        return FakeRunner(backend)

    with pytest.raises(PaperCycleServiceError) as caught:
        run_production_paper_cycle(
            ProductionPaperCycleSettings(),
            persistence=backend,
            runner_factory=runner_factory,
        )

    assert calls == 0
    assert caught.value.code == "storage_unavailable"
    assert caught.value.__cause__ is None


def test_worker_failure_writes_sanitized_error_status() -> None:
    backend = FakePersistence()

    class BrokenRunner:
        def run_once(self, **kwargs):
            del kwargs
            raise RuntimeError("postgresql://user:secret@example.invalid/private")

    with pytest.raises(PaperCycleServiceError) as caught:
        run_production_paper_cycle(
            ProductionPaperCycleSettings(),
            persistence=backend,
            runner_factory=lambda persistence: BrokenRunner(),
        )

    assert [status.engine_status for status in backend.statuses] == ["STARTING", "ERROR"]
    assert backend.statuses[-1].error == "RuntimeError: worker failure"
    assert caught.value.code == "execution_failed"
    assert caught.value.error_type == "RuntimeError"
    assert caught.value.__cause__ is None
    assert "secret" not in repr(caught.value)


def test_error_status_failure_does_not_mask_worker_failure() -> None:
    backend = FakePersistence()
    original_save = backend.save_runtime_status
    writes = 0

    def flaky_save(runtime_key, status):
        nonlocal writes
        writes += 1
        if writes >= 2:
            raise RuntimeError("status write failed with secret")
        original_save(runtime_key, status)

    backend.save_runtime_status = flaky_save

    class BrokenRunner:
        def run_once(self, **kwargs):
            del kwargs
            raise ValueError("provider secret")

    with pytest.raises(PaperCycleServiceError) as caught:
        run_production_paper_cycle(
            ProductionPaperCycleSettings(),
            persistence=backend,
            runner_factory=lambda persistence: BrokenRunner(),
        )

    assert caught.value.code == "execution_failed"
    assert caught.value.error_type == "ValueError"
    assert caught.value.__cause__ is None
```

Run:

```bash
pytest tests/test_paper_cycle_service.py -q
```

Expected RED: collection fails because `ai_trading.paper_cycle_service` does not exist.

### Step 1.2 — GREEN: implement the service

Create `src/ai_trading/paper_cycle_service.py`:

```python
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime

from .config import RiskConfig
from .paper_cycle import PaperCycleResult, PaperCycleRunner
from .persistence import PaperPersistence, build_runtime_key
from .persistence_factory import build_paper_persistence
from .runtime_status import HostedRuntimeStatus


@dataclass(frozen=True)
class ProductionPaperCycleSettings:
    symbol: str = "GC=F"
    period: str = "5d"
    interval: str = "5m"
    max_catchup_bars: int = 12
    poll_seconds: float = 300.0


class PaperCycleServiceError(RuntimeError):
    def __init__(self, *, code: str, error_type: str) -> None:
        super().__init__(code)
        self.code = code
        self.error_type = error_type


def _now_utc() -> str:
    return datetime.now(UTC).isoformat()


def _default_runner_factory(persistence: PaperPersistence) -> PaperCycleRunner:
    return PaperCycleRunner(persistence=persistence)
```

Implement this signature:

```python
def run_production_paper_cycle(
    settings: ProductionPaperCycleSettings,
    *,
    persistence: PaperPersistence | None = None,
    persistence_factory: Callable[[], PaperPersistence] = build_paper_persistence,
    runner_factory: Callable[[PaperPersistence], PaperCycleRunner] = _default_runner_factory,
) -> PaperCycleResult:
```

Behavior, in this exact order:

1. `settings.max_catchup_bars < 1` -> `ValueError` before state mutation.
2. Build backend only when `persistence is None`. Construction failure -> `PaperCycleServiceError(code="storage_unavailable", error_type=type(exc).__name__) from None`.
3. Compute `runtime_key = build_runtime_key(settings.symbol, settings.interval)` and `starting_cash = RiskConfig().starting_cash`.
4. Write STARTING in its own `try`. Failure -> `storage_unavailable` from None and no runner call.
5. In a second `try`, call:

```python
result = runner_factory(backend).run_once(
    symbol=settings.symbol,
    period=settings.period,
    interval=settings.interval,
    max_catchup_bars=settings.max_catchup_bars,
)
```

6. Load durable state, compute `equity = state.cash + state.units * state.last_price`, and write RUNNING with `last_cycle_timestamp=result.last_processed`, `processed=result.processed > 0`, `reason=result.reason`, durable units/processed bars, and `poll_seconds=settings.poll_seconds`.
7. Return the unchanged `PaperCycleResult`.
8. If step 5–6 raises, best-effort write ERROR with `error=f"{type(exc).__name__}: worker failure"`, then raise `PaperCycleServiceError(code="execution_failed", error_type=type(exc).__name__) from None`. Failure of the ERROR write must not replace the service error.

Run:

```bash
pytest tests/test_paper_cycle_service.py tests/test_paper_cycle.py -q
ruff check src/ai_trading/paper_cycle_service.py tests/test_paper_cycle_service.py
```

Expected GREEN.

### Step 1.3 — RED/GREEN: make CLI a thin adapter

Replace `tests/test_paper_cycle_cli.py` orchestration mocks with these two core tests (keep any existing CLI help/smoke tests that still apply):

```python
from typer.testing import CliRunner

from ai_trading import command_app
from ai_trading.paper_cycle import PaperCycleResult
from ai_trading.paper_cycle_service import PaperCycleServiceError, ProductionPaperCycleSettings


runner = CliRunner()


def test_cli_calls_shared_production_service(monkeypatch) -> None:
    seen = []

    def fake_service(settings):
        seen.append(settings)
        return PaperCycleResult(
            processed=1,
            remaining_backlog=False,
            last_processed="2026-09-16 08:00:00+00:00",
            processed_bars=4,
            reason="processed 1 bar(s)",
        )

    monkeypatch.setattr(command_app, "run_production_paper_cycle", fake_service)
    result = runner.invoke(
        command_app.app,
        ["paper-cycle", "--symbol", "GC=F", "--period", "5d", "--interval", "5m", "--max-catchup-bars", "12"],
    )

    assert result.exit_code == 0
    assert seen == [
        ProductionPaperCycleSettings(
            symbol="GC=F",
            period="5d",
            interval="5m",
            max_catchup_bars=12,
            poll_seconds=300.0,
        )
    ]
    assert "processed 1 bar(s)" in result.output


def test_cli_sanitizes_shared_service_failure(monkeypatch) -> None:
    def fail(settings):
        del settings
        raise PaperCycleServiceError(code="execution_failed", error_type="RuntimeError")

    monkeypatch.setattr(command_app, "run_production_paper_cycle", fail)
    result = runner.invoke(command_app.app, ["paper-cycle"])

    assert result.exit_code != 0
    assert "execution_failed" in result.output
    assert "RuntimeError" in result.output
    assert "postgresql://" not in result.output
```

Run the updated CLI tests first and verify RED because `command_app.py` still owns orchestration. Then refactor `paper_cycle()` to construct `ProductionPaperCycleSettings`, call `run_production_paper_cycle(settings)`, print only result summary, and catch only `PaperCycleServiceError`; raise `typer.Exit(code=1) from None`.

Verify:

```bash
pytest tests/test_paper_cycle_service.py tests/test_paper_cycle_cli.py tests/test_paper_cycle.py -q
ruff check src/ai_trading/command_app.py src/ai_trading/paper_cycle_service.py tests/test_paper_cycle_cli.py tests/test_paper_cycle_service.py
```

Commit:

```bash
git add src/ai_trading/paper_cycle_service.py src/ai_trading/command_app.py tests/test_paper_cycle_service.py tests/test_paper_cycle_cli.py
git commit -m "refactor: share production paper cycle service"
```

---

## Task 2: Authenticated Render Scheduler Endpoint

**Files**
- Create: `src/ai_trading/scheduler_endpoint.py`
- Create: `tests/test_scheduler_endpoint.py`
- Modify: `src/ai_trading/dashboard.py`
- Modify: `tests/test_dashboard_health.py`

### Step 2.1 — RED: pure endpoint adapter tests

Use this concrete helper in `tests/test_scheduler_endpoint.py`:

```python
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
```

Add these tests:

```python
def test_missing_server_token_fails_closed() -> None:
    response = handle_scheduler_request(
        authorization="Bearer supplied",
        configured_token="",
        run_cycle=lambda: successful_result(),
    )
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


def test_wrong_scheme_or_token_is_unauthorized() -> None:
    for authorization in ("Basic expected-token", "Bearer wrong-token"):
        response = handle_scheduler_request(
            authorization=authorization,
            configured_token="expected-token",
            run_cycle=lambda: successful_result(),
        )
        assert response.status_code == 401


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
        run_cycle=lambda: successful_result(reason="concurrent progress observed"),
    )
    assert response.status_code == 200
    assert response.payload["processed"] == 0


def test_service_failures_are_sanitized() -> None:
    for code, expected_status, expected_error in (
        ("storage_unavailable", 503, "storage unavailable"),
        ("execution_failed", 500, "worker failure"),
    ):
        def fail(code=code):
            raise PaperCycleServiceError(
                code=code,
                error_type="postgresql://user:secret@example.invalid/private",
            )

        response = handle_scheduler_request(
            authorization="Bearer expected-token",
            configured_token="expected-token",
            run_cycle=fail,
        )
        assert response.status_code == expected_status
        assert response.payload == {"ok": False, "error": expected_error}
        text = repr(response.payload)
        assert "secret" not in text
        assert "example.invalid" not in text
        assert "postgresql://" not in text
```

Run:

```bash
pytest tests/test_scheduler_endpoint.py -q
```

Expected RED: module does not exist.

### Step 2.2 — GREEN: pure adapter implementation

Create `src/ai_trading/scheduler_endpoint.py`:

```python
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
        return SchedulerHttpResponse(503, {"ok": False, "error": "scheduler unavailable"})
    if not _authorized(authorization, configured_token):
        return SchedulerHttpResponse(401, {"ok": False, "error": "unauthorized"})
    try:
        result = run_cycle()
    except PaperCycleServiceError as exc:
        if exc.code == "storage_unavailable":
            return SchedulerHttpResponse(503, {"ok": False, "error": "storage unavailable"})
        return SchedulerHttpResponse(500, {"ok": False, "error": "worker failure"})
    return SchedulerHttpResponse(
        200,
        {"ok": True, "processed": int(result.processed), "status": "RUNNING"},
    )
```

Do not catch arbitrary exceptions here; the shared service owns runtime-error sanitization and durable ERROR reporting.

Verify:

```bash
pytest tests/test_scheduler_endpoint.py -q
ruff check src/ai_trading/scheduler_endpoint.py tests/test_scheduler_endpoint.py
```

### Step 2.3 — RED/GREEN: HTTP server integration

Append concrete helpers to `tests/test_scheduler_endpoint.py`:

```python
import json
import socket
import time
from threading import Thread
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from ai_trading.file_persistence import FilePaperPersistence
from ai_trading.hosted_runtime import HostedPaperSettings
from ai_trading.dashboard import serve_dashboard


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _post(url: str, *, authorization: str | None = None, body: bytes | None = None):
    headers = {"Content-Type": "application/json"}
    if authorization is not None:
        headers["Authorization"] = authorization
    request = Request(url, data=body or b"", headers=headers, method="POST")
    try:
        with urlopen(request, timeout=2) as response:
            return response.status, response.read().decode()
    except HTTPError as exc:
        return exc.code, exc.read().decode()


def _start_scheduler_server(tmp_path, executor, *, token="server-secret") -> int:
    port = _free_port()
    thread = Thread(
        target=serve_dashboard,
        kwargs={
            "host": "127.0.0.1",
            "port": port,
            "persistence": FilePaperPersistence(root=tmp_path),
            "settings": HostedPaperSettings(
                enabled=False,
                external_scheduler=True,
                symbol="GC=F",
                period="5d",
                interval="5m",
            ),
            "scheduler_token": token,
            "paper_cycle_executor": executor,
        },
        daemon=True,
    )
    thread.start()
    deadline = time.time() + 3
    while time.time() < deadline:
        try:
            with urlopen(f"http://127.0.0.1:{port}/healthz", timeout=1):
                return port
        except URLError:
            time.sleep(0.02)
    raise AssertionError("scheduler test server did not start")
```

Add tests:

```python
def test_http_scheduler_auth_and_body_cannot_override_settings(tmp_path) -> None:
    calls = 0

    def executor():
        nonlocal calls
        calls += 1
        return successful_result(processed=1, reason="processed 1 bar(s)")

    port = _start_scheduler_server(tmp_path, executor)
    url = f"http://127.0.0.1:{port}/internal/paper-cycle"

    assert _post(url)[0] == 401
    assert _post(url, authorization="Bearer wrong")[0] == 401
    status, body = _post(
        url + "?symbol=SI%3DF&interval=1m",
        authorization="Bearer server-secret",
        body=json.dumps({"symbol": "SI=F", "interval": "1m"}).encode(),
    )
    assert status == 200
    assert calls == 1
    assert json.loads(body) == {"ok": True, "processed": 1, "status": "RUNNING"}


def test_http_scheduler_rejects_other_post_paths(tmp_path) -> None:
    port = _start_scheduler_server(tmp_path, lambda: successful_result())
    assert _post(f"http://127.0.0.1:{port}/api/status", authorization="Bearer server-secret")[0] == 404


def test_http_scheduler_error_payload_never_exposes_internal_details(tmp_path) -> None:
    def fail():
        raise PaperCycleServiceError(
            code="execution_failed",
            error_type="postgresql://user:secret@example.invalid/private",
        )

    port = _start_scheduler_server(tmp_path, fail)
    status, body = _post(
        f"http://127.0.0.1:{port}/internal/paper-cycle",
        authorization="Bearer server-secret",
    )
    assert status == 500
    assert json.loads(body) == {"ok": False, "error": "worker failure"}
    assert "secret" not in body
    assert "example.invalid" not in body
```

Run before production edit and verify RED because `serve_dashboard()` lacks these arguments/POST route.

Then modify `dashboard.py`:

```python
scheduler_token: str | None = None,
paper_cycle_executor: Callable[[], PaperCycleResult] | None = None,
```

Resolve token once at startup from injected value or `os.getenv("AI_TRADING_SCHEDULER_TOKEN", "").strip()`.

If no injected executor exists, define a zero-arg closure calling `run_production_paper_cycle()` with the existing `backend` and:

```python
ProductionPaperCycleSettings(
    symbol=effective_settings.symbol,
    period=effective_settings.period,
    interval=effective_settings.interval,
    max_catchup_bars=12,
    poll_seconds=300.0,
)
```

Change `_send_json` to accept `status_code: int = 200`. Add `do_POST()` using only `urlsplit(self.path).path.rstrip("/")`; only `/internal/paper-cycle` calls `handle_scheduler_request()`. Do not parse request body/query for trading configuration. Other POST paths return 404. Keep `log_message()` suppressed.

Verify:

```bash
pytest tests/test_scheduler_endpoint.py tests/test_dashboard_health.py tests/test_dashboard_persistence.py tests/test_dashboard.py -q
ruff check src/ai_trading/dashboard.py src/ai_trading/scheduler_endpoint.py tests/test_scheduler_endpoint.py
```

Commit:

```bash
git add src/ai_trading/scheduler_endpoint.py src/ai_trading/dashboard.py tests/test_scheduler_endpoint.py tests/test_dashboard_health.py
git commit -m "feat: add authenticated paper cycle endpoint"
```

---

## Task 3: Minimal Cloudflare Cron Worker + CI

**Files**
- Create: `infra/cloudflare-paper-scheduler/package.json`
- Create: `infra/cloudflare-paper-scheduler/src/index.js`
- Create: `infra/cloudflare-paper-scheduler/test/index.test.js`
- Create: `infra/cloudflare-paper-scheduler/wrangler.toml`
- Create: `infra/cloudflare-paper-scheduler/README.md`
- Modify: `.github/workflows/ci.yml`

### Step 3.1 — RED: Worker tests

Create `infra/cloudflare-paper-scheduler/package.json`:

```json
{
  "name": "ai-trading-paper-scheduler",
  "private": true,
  "type": "module",
  "scripts": {"test": "node --test test/index.test.js"}
}
```

Create `infra/cloudflare-paper-scheduler/test/index.test.js`:

```javascript
import assert from "node:assert/strict";
import test from "node:test";
import worker, { invokePaperCycle } from "../src/index.js";

const env = {
  TARGET_URL: "https://example.test/internal/paper-cycle",
  SCHEDULER_TOKEN: "scheduler-secret",
};

test("invokePaperCycle sends only the authenticated POST", async () => {
  let seen;
  await invokePaperCycle(env, async (url, options) => {
    seen = { url, options };
    return { ok: true, status: 200 };
  });
  assert.equal(seen.url, env.TARGET_URL);
  assert.equal(seen.options.method, "POST");
  assert.equal(seen.options.headers.Authorization, "Bearer scheduler-secret");
  assert.equal(seen.options.headers["User-Agent"], "ai-trading-cloudflare-scheduler/1");
  assert.equal("body" in seen.options, false);
});

test("missing bindings fail before fetch", async () => {
  for (const missing of ["TARGET_URL", "SCHEDULER_TOKEN"]) {
    const broken = { ...env };
    delete broken[missing];
    let calls = 0;
    await assert.rejects(
      invokePaperCycle(broken, async () => {
        calls += 1;
        return { ok: true, status: 200 };
      }),
      { message: "scheduler configuration missing" },
    );
    assert.equal(calls, 0);
  }
});

test("non-2xx error leaks neither token nor response body", async () => {
  await assert.rejects(
    invokePaperCycle(env, async () => ({
      ok: false,
      status: 503,
      text: async () => "private-response-secret",
    })),
    (error) => {
      assert.equal(error.message, "paper cycle failed with HTTP 503");
      assert.equal(error.message.includes("scheduler-secret"), false);
      assert.equal(error.message.includes("private-response-secret"), false);
      return true;
    },
  );
});

test("scheduled handler registers the invocation with waitUntil", async () => {
  const originalFetch = globalThis.fetch;
  let pending;
  globalThis.fetch = async () => ({ ok: true, status: 200 });
  try {
    worker.scheduled({}, env, { waitUntil(promise) { pending = promise; } });
    assert.ok(pending);
    await pending;
  } finally {
    globalThis.fetch = originalFetch;
  }
});
```

Run:

```bash
npm test --prefix infra/cloudflare-paper-scheduler
```

Expected RED: `src/index.js` is missing.

### Step 3.2 — GREEN: Worker implementation/config/docs

Create `src/index.js`:

```javascript
export async function invokePaperCycle(env, fetchImpl = fetch) {
  if (!env.TARGET_URL || !env.SCHEDULER_TOKEN) {
    throw new Error("scheduler configuration missing");
  }
  const response = await fetchImpl(env.TARGET_URL, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${env.SCHEDULER_TOKEN}`,
      "User-Agent": "ai-trading-cloudflare-scheduler/1",
    },
  });
  if (!response.ok) {
    throw new Error(`paper cycle failed with HTTP ${response.status}`);
  }
}

export default {
  scheduled(_event, env, ctx) {
    ctx.waitUntil(invokePaperCycle(env));
  },
};
```

Create `wrangler.toml`:

```toml
name = "ai-trading-paper-scheduler"
main = "src/index.js"
compatibility_date = "2026-09-16"

[triggers]
crons = ["*/5 * * * *"]

[vars]
TARGET_URL = "https://ai-trading-dashboard-qyr2.onrender.com/internal/paper-cycle"
```

Do not put `SCHEDULER_TOKEN` in Wrangler.

Create README documenting exactly: Worker name `ai-trading-paper-scheduler`; root directory `infra/cloudflare-paper-scheduler`; `TARGET_URL` is non-secret; `SCHEDULER_TOKEN` is a Cloudflare Secret; cron is Wrangler-managed; Worker has no DB credential/trading settings; rollback disables cron while GitHub manual fallback remains.

Verify:

```bash
npm test --prefix infra/cloudflare-paper-scheduler
```

### Step 3.3 — CI

Add Node setup after Python setup:

```yaml
      - uses: actions/setup-node@v4
        with:
          node-version: "22"
```

Add after Pytest:

```yaml
      - name: Cloudflare Worker tests
        run: npm test --prefix infra/cloudflare-paper-scheduler
```

No `npm install` is required.

Run:

```bash
npm test --prefix infra/cloudflare-paper-scheduler
ruff check src tests
pytest -q
```

Secret scan committed content for `postgresql://`, plaintext scheduler-token assignments, and secret-looking auth literals. `Authorization: Bearer` may appear only as source code constructing the header, never with a real token value.

Commit:

```bash
git add infra/cloudflare-paper-scheduler .github/workflows/ci.yml
git commit -m "feat: add Cloudflare paper scheduler worker"
```

---

## Task 4: First PR and Render Deployment (GitHub Schedule Still Present)

1. Verify `pytest tests/test_paper_cycle_workflow.py -q` stays green and `.github/workflows/paper-cycle.yml` still has both `schedule:` and `workflow_dispatch:`.
2. Fresh full checks:

```bash
ruff check src tests
pytest -q
npm test --prefix infra/cloudflare-paper-scheduler
```

3. Review diff against spec: no request-controlled trading settings; timing-safe compare; missing token fail-closed; shared CLI/HTTP service; sanitized failures; Worker never reads failure body; no Neon credential; GitHub schedule unchanged; live trading disabled.
4. Open draft PR titled `feat: add Cloudflare paper scheduler path`, explicitly stating GitHub automatic scheduling remains during transition.
5. Require exact-head CI green for Python install, Ruff, full Pytest/PostgreSQL 16, and Worker tests. Resolve material findings, mark Ready, merge with expected head SHA.
6. Require main CI green and Render auto-deploy live.
7. Before token configuration, unauthenticated POST to `https://ai-trading-dashboard-qyr2.onrender.com/internal/paper-cycle` must return sanitized 503 `scheduler unavailable`; verify rejected request did not mutate Neon and Render remains dashboard-only.

---

## Task 5: Manual Cloudflare Boundary + First Production Proof

No Cloudflare connector exists, so only this account setup is manual.

1. Tell user to generate at least 32 random bytes as URL-safe text using a password manager/trusted local generator. **Never paste the token into ChatGPT.**
2. User: Render `ai-trading-dashboard -> Environment -> Add Environment Variable`; name `AI_TRADING_SCHEDULER_TOKEN`, value private token; save/redeploy.
3. Assistant: verify Render live, log still says `Hosted paper worker: external scheduler enabled`, unauthenticated POST is now 401, Neon unchanged.
4. User validates one authorized request without revealing token. Preferred local shell:

```bash
export SCHEDULER_TOKEN='value stored in your password manager'
curl -i -X POST \
  -H "Authorization: Bearer ${SCHEDULER_TOKEN}" \
  https://ai-trading-dashboard-qyr2.onrender.com/internal/paper-cycle
unset SCHEDULER_TOKEN
```

Expected: HTTP 200 and JSON containing only `ok`, `processed`, `status`. User reports only status/non-secret fields. If no shell, use a trusted local HTTP client; never a public request-sharing service.
5. Assistant verifies fresh Neon heartbeat/state after authorized call.
6. User: Cloudflare `Workers & Pages -> Create application -> Import a repository`; choose `dbrckk/Ai-trading`; root `infra/cloudflare-paper-scheduler`; Worker name `ai-trading-paper-scheduler`; Save and Deploy.
7. User: Worker `Settings -> Variables and Secrets -> Add`; type `Secret`; name `SCHEDULER_TOKEN`; same private token; deploy.
8. User: Worker `Settings -> Triggers -> Cron Triggers`; confirm `*/5 * * * *`. Do not add a duplicate if Wrangler already created it.
9. Assistant records Neon before/after runtime key, revision, `last_processed`, `processed_bars`, model metadata/checksum, status heartbeat, engine status. A refreshed scheduled heartbeat is sufficient when there is no new eligible bar.
10. Update issue #19 with first Cloudflare scheduled proof; keep it open pending cutover and second proof.

---

## Task 6: Second PR — GitHub Manual Fallback Only

Do not start until Task 5 has real Cloudflare scheduled-heartbeat evidence.

**Files**
- Modify `.github/workflows/paper-cycle.yml`
- Modify `tests/test_paper_cycle_workflow.py`
- Modify `README.md`

### Step 6.1 — RED

Change workflow test required strings to keep `workflow_dispatch:`, DB secret reference/preflight, concurrency guard, and exact manual command. Add forbidden strings:

```python
for forbidden in (
    "schedule:",
    "cron:",
    "postgresql://",
    "postgres://",
    "password=",
):
    assert forbidden not in text
```

Run:

```bash
pytest tests/test_paper_cycle_workflow.py -q
```

Expected RED because current workflow still has schedule/cron.

### Step 6.2 — GREEN

Workflow trigger becomes:

```yaml
on:
  workflow_dispatch:
```

Keep job permissions, concurrency, DB secret/preflight, Python setup, install, and exact `ai-trading paper-cycle --symbol GC=F --period 5d --interval 5m --max-catchup-bars 12` unchanged.

README production diagram becomes:

```text
Cloudflare Cron (every 5 minutes)
        |
        v
POST /internal/paper-cycle on Render
        |
        v
shared production paper-cycle service
        |
        v
Neon PostgreSQL durable state
        |
        +----------------------+
        |                      |
        v                      v
paper state/model/trades     Render dashboard
```

Document GitHub `workflow_dispatch` as manual fallback and `AI_TRADING_SCHEDULER_TOKEN` by variable name only.

Verify:

```bash
pytest tests/test_paper_cycle_workflow.py tests/test_scheduler_endpoint.py tests/test_paper_cycle_service.py tests/test_paper_cycle_cli.py -q
ruff check src tests
pytest -q
npm test --prefix infra/cloudflare-paper-scheduler
```

Open PR `ops: make Cloudflare the paper scheduler`, include first Cloudflare heartbeat evidence, require exact-head CI green, merge, then verify main CI and Render live.

---

## Task 7: Second Cloudflare Proof + Closure

1. Observe a new Cloudflare-scheduled heartbeat after GitHub schedule removal using Neon `paper_runtime_status.updated_at_utc`.
2. Confirm runtime key unchanged, revision/processed_bars nondecreasing, model present, no duplicate logical trade/audit event for one execution bar, dashboard fresh RUNNING, Render still external-scheduler mode, and no live broker route/credential.
3. Verify GitHub workflow still contains `workflow_dispatch` and durable DB preflight; do not trigger a redundant cycle merely for ceremony.
4. Update issue #19 with Worker name, cron, both observed scheduled heartbeats separated by cutover, Render dashboard-only status, Neon continuity, GitHub manual fallback; close as completed.
5. Fresh final evidence before completion claim:

```bash
ruff check src tests
pytest -q
npm test --prefix infra/cloudflare-paper-scheduler
```

Also require current main CI success, current Render live status, and current Neon continuity evidence.

## Rollback

If Cloudflare scheduling fails after cutover: user disables Cloudflare cron; Render remains `AI_TRADING_EXTERNAL_SCHEDULER=1`; GitHub `workflow_dispatch` provides manual one-shot execution; restoring GitHub automatic schedule requires reviewed RED/GREEN change; Neon runtime/model/trade/audit state is not rolled back because scheduler replacement owns no durable trading state.

## Definition of Done

- CLI and HTTP share one durable production-cycle service.
- Unauthorized or misconfigured endpoint fails closed.
- Scheduler token never appears in Git, logs, responses, issue text, or chat.
- Worker has no trading logic/DB credential and fails closed on missing bindings.
- Worker tests run in CI.
- One real Cloudflare cron heartbeat is proven before GitHub schedule removal.
- GitHub retains `workflow_dispatch` but no automatic schedule after cutover.
- A second Cloudflare heartbeat is proven after cutover.
- Neon state/model continuity remains intact.
- Render remains dashboard-only.
- Dashboard freshness reflects scheduler failures.
- Python and Worker suites are green.
- Issue #19 closes only after production evidence.
- Live trading remains disabled.
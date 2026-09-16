# Cloudflare Paper Scheduler Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the unreliable automatic GitHub Actions trigger with a free Cloudflare Cron Trigger that securely wakes Render every five minutes, while keeping the existing paper-only execution path, Neon durability, catch-up semantics, and GitHub manual fallback.

**Architecture:** Extract the existing CLI paper-cycle orchestration into one shared Python service, expose that service through an authenticated `POST /internal/paper-cycle` endpoint on Render, and add a minimal scheduled Cloudflare Worker that only sends an authenticated POST. Neon remains the only durable state store. The first implementation PR deliberately leaves the GitHub `schedule:` block in place. Only after a real Cloudflare scheduled invocation is proven in production does a second PR remove GitHub automatic scheduling and retain `workflow_dispatch` only.

**Tech Stack:** Python 3.11+, stdlib `http.server`, Typer, psycopg 3, River/joblib, PostgreSQL 16-compatible Neon, Render Free web service, Cloudflare Workers Cron, Node.js built-in test runner, GitHub Actions, pytest, Ruff.

**Spec:** `docs/superpowers/specs/2026-09-16-cloudflare-paper-scheduler-design.md`

## Global Constraints

- Paper trading only. Do not add a live broker adapter, live broker credential, or real-order route.
- Stable production runtime key remains `paper:GC=F:5m:online-river:v1` through `build_runtime_key()`.
- Production symbol, period, interval, catch-up limit, and risk settings are server-side only. The HTTP request must not override them.
- Production values remain symbol `GC=F`, period `5d`, interval `5m`, maximum 12 catch-up bars, and status poll/freshness cadence 300 seconds.
- `AI_TRADING_DATABASE_URL` remains the only production database selector. If configured and unusable, execution fails closed with no file fallback.
- `AI_TRADING_EXTERNAL_SCHEDULER=1` remains enabled on Render; the embedded daemon must stay disabled.
- The scheduler credential is separate from every database, GitHub, Render, and Cloudflare credential.
- Never commit, print, return, or put in issue/PR text the scheduler token, database URL, database host, or raw provider exception.
- Cloudflare contains no model state, market data logic, trading logic, or Neon credential.
- At-least-once delivery is expected. Existing durable `last_processed` and PostgreSQL revision CAS remain the correctness boundary.
- A benign persistence race is a successful logical no-op, not an HTTP failure.
- Do not remove the GitHub Actions `schedule:` block in the first implementation PR. Remove it only after one real Cloudflare scheduled invocation is observed in production.
- Do not close issue #19 until a second Cloudflare scheduled invocation is observed after GitHub automatic scheduling has been removed.
- Do not delete the temporary Render PostgreSQL instance without explicit user approval.

---

### Task 1: Extract One Shared Production Paper-Cycle Service

**Files:**
- Create: `src/ai_trading/paper_cycle_service.py`
- Create: `tests/test_paper_cycle_service.py`
- Modify: `src/ai_trading/command_app.py`
- Modify: `tests/test_paper_cycle_cli.py`

**Interfaces:**
- Consumes: `PaperCycleRunner`, `PaperPersistence`, `build_paper_persistence()`, `build_runtime_key()`, `RiskConfig`, and `HostedRuntimeStatus`.
- Produces: `ProductionPaperCycleSettings`, `PaperCycleServiceError`, and `run_production_paper_cycle()`.
- `run_production_paper_cycle()` returns the existing `PaperCycleResult` so CLI and HTTP use exactly the same execution result type.

- [ ] **Step 1: Write RED tests for the shared service**

Create `tests/test_paper_cycle_service.py` with a fake persistence containing a deterministic `RuntimeState`, plus a fake runner factory. Cover these cases:

```python
def test_service_persists_starting_and_running_status() -> None:
    backend = FakePersistence()
    settings = ProductionPaperCycleSettings()

    result = run_production_paper_cycle(
        settings,
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
```

Add a backend-construction failure test that passes a `persistence_factory` raising an exception whose message contains a fake PostgreSQL URL and secret. Assert the raised `PaperCycleServiceError` has `code == "storage_unavailable"`, exposes only the exception type through `error_type`, and neither `str(error)` nor `repr(error)` contains the fake URL, host, or password.

Add a runner-failure test. Assert best-effort durable `ERROR` is written with `error == "RuntimeError: worker failure"`, then `PaperCycleServiceError.code == "execution_failed"` is raised without the original message or chained secret-bearing exception.

Add a failure test where saving `ERROR` itself raises. Assert the service still raises only the sanitized `PaperCycleServiceError` and does not replace it with the status-store exception.

- [ ] **Step 2: Verify RED**

Run:

```bash
pytest tests/test_paper_cycle_service.py -q
```

Expected: collection fails because `ai_trading.paper_cycle_service` does not exist.

- [ ] **Step 3: Implement the shared service**

Create `src/ai_trading/paper_cycle_service.py` around these concrete types:

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

Implement:

```python
def run_production_paper_cycle(
    settings: ProductionPaperCycleSettings,
    *,
    persistence: PaperPersistence | None = None,
    persistence_factory: Callable[[], PaperPersistence] = build_paper_persistence,
    runner_factory: Callable[[PaperPersistence], PaperCycleRunner] = _default_runner_factory,
) -> PaperCycleResult:
```

The function must:

1. reject `max_catchup_bars < 1` with `ValueError` before any state mutation;
2. construct the backend only when `persistence is None`;
3. convert backend-construction failure to `PaperCycleServiceError(code="storage_unavailable", error_type=type(exc).__name__) from None`;
4. write `STARTING` with `RiskConfig().starting_cash` and `settings.poll_seconds`;
5. call `runner_factory(backend).run_once()` with the five exact settings fields relevant to the runner;
6. load durable state after the runner finishes;
7. calculate equity as `state.cash + state.units * state.last_price`;
8. write `RUNNING` using `result.last_processed`, `result.processed > 0`, `result.reason`, durable units, durable processed-bar count, and the configured poll interval;
9. return the unchanged `PaperCycleResult`;
10. on an exception after backend creation, make one best-effort `ERROR` status write with sanitized `error=f"{type(exc).__name__}: worker failure"`, then raise `PaperCycleServiceError(code="execution_failed", error_type=type(exc).__name__) from None`.

Treat failure of the initial `STARTING` status write as `storage_unavailable`; no market-data or runner work may start if the durable status store cannot be initialized.

- [ ] **Step 4: Verify the service GREEN**

Run:

```bash
pytest tests/test_paper_cycle_service.py tests/test_paper_cycle.py -q
ruff check src/ai_trading/paper_cycle_service.py tests/test_paper_cycle_service.py
```

Expected: PASS.

- [ ] **Step 5: Refactor the CLI into a thin adapter**

First update `tests/test_paper_cycle_cli.py` so it monkeypatches `command_app.run_production_paper_cycle` instead of mocking persistence and `PaperCycleRunner` inside the CLI module. The success test must assert that the adapter builds:

```python
ProductionPaperCycleSettings(
    symbol="GC=F",
    period="5d",
    interval="5m",
    max_catchup_bars=12,
    poll_seconds=300.0,
)
```

and prints only a sanitized summary based on the returned `PaperCycleResult`.

The failure test must raise:

```python
PaperCycleServiceError(code="execution_failed", error_type="RuntimeError")
```

and assert CLI exit code is non-zero without any provider detail.

Run the updated CLI test before editing production code and confirm it fails because `command_app.py` still owns orchestration.

Then replace orchestration in `command_app.paper_cycle()` with one call to `run_production_paper_cycle(settings)`. Catch only `PaperCycleServiceError`, print a generic message containing `code` and `error_type`, and raise `typer.Exit(code=1) from None`.

- [ ] **Step 6: Verify CLI and shared-service GREEN**

Run:

```bash
pytest tests/test_paper_cycle_service.py tests/test_paper_cycle_cli.py tests/test_paper_cycle.py -q
ruff check src/ai_trading/command_app.py src/ai_trading/paper_cycle_service.py tests/test_paper_cycle_cli.py tests/test_paper_cycle_service.py
```

Expected: PASS.

- [ ] **Step 7: Commit Task 1**

```bash
git add src/ai_trading/paper_cycle_service.py src/ai_trading/command_app.py tests/test_paper_cycle_service.py tests/test_paper_cycle_cli.py
git commit -m "refactor: share production paper cycle service"
```

---

### Task 2: Add the Authenticated Render Scheduler Endpoint

**Files:**
- Create: `src/ai_trading/scheduler_endpoint.py`
- Create: `tests/test_scheduler_endpoint.py`
- Modify: `src/ai_trading/dashboard.py`
- Modify: `tests/test_dashboard_health.py`

**Interfaces:**
- Pure adapter: `handle_scheduler_request()` maps authorization + service result to a sanitized HTTP response.
- HTTP route: `POST /internal/paper-cycle`.
- Production credential: Render environment variable `AI_TRADING_SCHEDULER_TOKEN`.
- Production executor: the shared `run_production_paper_cycle()` using the dashboard's already-constructed persistence backend.

- [ ] **Step 1: Write RED pure endpoint tests**

Create `tests/test_scheduler_endpoint.py` with these concrete cases:

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


def test_wrong_scheme_is_unauthorized() -> None:
    response = handle_scheduler_request(
        authorization="Basic expected-token",
        configured_token="expected-token",
        run_cycle=lambda: successful_result(),
    )
    assert response.status_code == 401


def test_wrong_bearer_token_is_unauthorized() -> None:
    response = handle_scheduler_request(
        authorization="Bearer wrong-token",
        configured_token="expected-token",
        run_cycle=lambda: successful_result(),
    )
    assert response.status_code == 401


def test_valid_token_runs_exactly_one_cycle() -> None:
    calls = 0

    def run_cycle() -> PaperCycleResult:
        nonlocal calls
        calls += 1
        return successful_result(processed=2)

    response = handle_scheduler_request(
        authorization="Bearer expected-token",
        configured_token="expected-token",
        run_cycle=run_cycle,
    )

    assert calls == 1
    assert response.status_code == 200
    assert response.payload == {"ok": True, "processed": 2, "status": "RUNNING"}
```

Add a `processed=0` / `reason="concurrent progress observed"` case and assert HTTP 200. Add one `storage_unavailable` service error mapping to 503 and one `execution_failed` mapping to 500. For both, assert payloads contain no `error_type`, token, database URL, or raw provider message.

- [ ] **Step 2: Verify RED**

Run:

```bash
pytest tests/test_scheduler_endpoint.py -q
```

Expected: collection fails because `ai_trading.scheduler_endpoint` does not exist.

- [ ] **Step 3: Implement the pure adapter**

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
```

Implement `handle_scheduler_request()` with this order:

1. empty `configured_token` -> 503, without calling `run_cycle`;
2. missing/wrong Authorization -> 401, without calling `run_cycle`;
3. valid token -> call `run_cycle()` exactly once;
4. successful result -> 200 with only `ok`, integer `processed`, and `status="RUNNING"`;
5. `PaperCycleServiceError.code == "storage_unavailable"` -> 503 with `{"ok": False, "error": "storage unavailable"}`;
6. every other `PaperCycleServiceError` -> 500 with `{"ok": False, "error": "worker failure"}`.

Do not catch arbitrary exceptions here. The shared service is the sanitizing boundary; an unexpected programming error should surface to the server integration test rather than be accidentally normalized without a durable `ERROR` write.

- [ ] **Step 4: Verify pure adapter GREEN**

Run:

```bash
pytest tests/test_scheduler_endpoint.py -q
ruff check src/ai_trading/scheduler_endpoint.py tests/test_scheduler_endpoint.py
```

Expected: PASS.

- [ ] **Step 5: Write RED HTTP integration tests**

Extend `tests/test_scheduler_endpoint.py` with a local `ThreadingHTTPServer` fixture using `serve_dashboard()` injection arguments:

```python
scheduler_token="server-secret"
paper_cycle_executor=fake_cycle
```

Use `urllib.request.Request` with method `POST`. Assert:

- `/internal/paper-cycle` without Authorization -> 401;
- wrong token -> 401;
- valid token -> 200 and fake cycle called exactly once;
- a JSON body containing `{"symbol":"SI=F","interval":"1m"}` does not reach the executor and does not alter the result;
- `POST /api/status` -> 404;
- a fake service failure containing secret-looking text cannot put that text into the HTTP response.

- [ ] **Step 6: Verify HTTP integration RED**

Run:

```bash
pytest tests/test_scheduler_endpoint.py tests/test_dashboard_health.py -q
```

Expected: FAIL because `serve_dashboard()` has no POST route or scheduler injection arguments.

- [ ] **Step 7: Wire the endpoint into `dashboard.py`**

Add imports for `Callable`, `ProductionPaperCycleSettings`, `run_production_paper_cycle`, `PaperCycleResult`, and `handle_scheduler_request`.

Extend `serve_dashboard()` keyword arguments with:

```python
scheduler_token: str | None = None,
paper_cycle_executor: Callable[[], PaperCycleResult] | None = None,
```

Resolve the production token once during startup:

```python
effective_scheduler_token = (
    scheduler_token
    if scheduler_token is not None
    else os.getenv("AI_TRADING_SCHEDULER_TOKEN", "").strip()
)
```

If `paper_cycle_executor` is absent, create a closure that calls `run_production_paper_cycle()` with the already constructed `backend` and:

```python
ProductionPaperCycleSettings(
    symbol=effective_settings.symbol,
    period=effective_settings.period,
    interval=effective_settings.interval,
    max_catchup_bars=12,
    poll_seconds=300.0,
)
```

Change `_send_json` to accept `status_code: int = 200` and call `self.send_response(status_code)`.

Add `do_POST()` that resolves only the URL path with `urlsplit(self.path).path.rstrip("/")`. Only `/internal/paper-cycle` is accepted. Pass `self.headers.get("Authorization")`, the resolved token, and the zero-argument executor to `handle_scheduler_request()`, then send its exact sanitized payload/status. Do not parse the request body or query parameters for trading configuration.

Keep `log_message()` suppressed so Authorization headers cannot enter access logs through this server implementation.

- [ ] **Step 8: Verify endpoint GREEN and no dashboard regression**

Run:

```bash
pytest tests/test_scheduler_endpoint.py tests/test_dashboard_health.py tests/test_dashboard_persistence.py tests/test_dashboard.py -q
ruff check src/ai_trading/dashboard.py src/ai_trading/scheduler_endpoint.py tests/test_scheduler_endpoint.py
```

Expected: PASS.

- [ ] **Step 9: Commit Task 2**

```bash
git add src/ai_trading/scheduler_endpoint.py src/ai_trading/dashboard.py tests/test_scheduler_endpoint.py tests/test_dashboard_health.py
git commit -m "feat: add authenticated paper cycle endpoint"
```

---

### Task 3: Add the Minimal Cloudflare Cron Worker and CI Coverage

**Files:**
- Create: `infra/cloudflare-paper-scheduler/package.json`
- Create: `infra/cloudflare-paper-scheduler/src/index.js`
- Create: `infra/cloudflare-paper-scheduler/test/index.test.js`
- Create: `infra/cloudflare-paper-scheduler/wrangler.toml`
- Create: `infra/cloudflare-paper-scheduler/README.md`
- Modify: `.github/workflows/ci.yml`

**Interfaces:**
- Cloudflare variable: `TARGET_URL`.
- Cloudflare secret: `SCHEDULER_TOKEN`.
- Cron: `*/5 * * * *` in UTC.
- Target: `https://ai-trading-dashboard-qyr2.onrender.com/internal/paper-cycle`.

- [ ] **Step 1: Write the Worker tests first**

Create `infra/cloudflare-paper-scheduler/package.json`:

```json
{
  "name": "ai-trading-paper-scheduler",
  "private": true,
  "type": "module",
  "scripts": {
    "test": "node --test test/index.test.js"
  }
}
```

Create `infra/cloudflare-paper-scheduler/test/index.test.js` importing `invokePaperCycle` from `../src/index.js`. Test that a fake `fetchImpl` receives exactly:

- the configured `TARGET_URL`;
- method `POST`;
- `Authorization: Bearer scheduler-secret`;
- `User-Agent: ai-trading-cloudflare-scheduler/1`;
- no request body.

Add a non-2xx test with fake HTTP 503. Assert rejection message is exactly `paper cycle failed with HTTP 503` and does not contain the token or a fake secret response body.

Add a scheduled-handler test by temporarily replacing `globalThis.fetch`, capturing the promise passed to `ctx.waitUntil()`, awaiting it, and restoring the original `globalThis.fetch` in a `finally` block.

- [ ] **Step 2: Verify Worker RED**

Run:

```bash
npm test --prefix infra/cloudflare-paper-scheduler
```

Expected: FAIL because `src/index.js` does not exist.

- [ ] **Step 3: Implement the Worker**

Create `infra/cloudflare-paper-scheduler/src/index.js`:

```javascript
export async function invokePaperCycle(env, fetchImpl = fetch) {
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

Do not call `response.text()`, do not log the Authorization header, and do not send any trading parameters.

- [ ] **Step 4: Add Wrangler configuration**

Create `infra/cloudflare-paper-scheduler/wrangler.toml`:

```toml
name = "ai-trading-paper-scheduler"
main = "src/index.js"
compatibility_date = "2026-09-16"

[triggers]
crons = ["*/5 * * * *"]

[vars]
TARGET_URL = "https://ai-trading-dashboard-qyr2.onrender.com/internal/paper-cycle"
```

Do not add `SCHEDULER_TOKEN` to this file.

- [ ] **Step 5: Document deployment without secrets**

Create `infra/cloudflare-paper-scheduler/README.md` documenting:

- Worker name must be `ai-trading-paper-scheduler` because Cloudflare Git integration requires it to match Wrangler configuration;
- repository root directory for Workers Builds is `infra/cloudflare-paper-scheduler`;
- `TARGET_URL` is committed and non-secret;
- `SCHEDULER_TOKEN` must be added as a Cloudflare Secret, never a plaintext variable;
- Cron is managed by `wrangler.toml`, not duplicated manually;
- the Worker has no database credential and no trading configuration;
- rollback means disabling the Cron Trigger while keeping GitHub `workflow_dispatch` available.

- [ ] **Step 6: Verify Worker GREEN**

Run:

```bash
npm test --prefix infra/cloudflare-paper-scheduler
```

Expected: all Worker tests pass.

- [ ] **Step 7: Add Worker tests to CI**

Update `.github/workflows/ci.yml` after Python setup with:

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

No `npm install` step is required because the test harness uses only Node built-ins and the Worker has no package dependency.

- [ ] **Step 8: Run focused and full verification**

Run:

```bash
npm test --prefix infra/cloudflare-paper-scheduler
ruff check src tests
pytest -q
```

Expected: PASS.

- [ ] **Step 9: Secret scan**

Run repository searches for all of these strings and confirm there is no production credential value:

```text
postgresql://
AI_TRADING_SCHEDULER_TOKEN=
SCHEDULER_TOKEN=
Authorization: Bearer
```

The source-code string `Authorization: Bearer` may appear only as code constructing the header; no token value may follow it in a committed file.

- [ ] **Step 10: Commit Task 3**

```bash
git add infra/cloudflare-paper-scheduler .github/workflows/ci.yml
git commit -m "feat: add Cloudflare paper scheduler worker"
```

---

### Task 4: First PR, Review, Merge, and Render Endpoint Deployment

**Files:**
- Review all files changed in Tasks 1-3.
- Do not modify `.github/workflows/paper-cycle.yml` yet.
- Do not rewrite the main README to claim Cloudflare is live yet.

- [ ] **Step 1: Verify the GitHub workflow still has its current automatic schedule**

Run:

```bash
pytest tests/test_paper_cycle_workflow.py -q
```

and inspect `.github/workflows/paper-cycle.yml`. It must still contain both `schedule:` with the existing cron and `workflow_dispatch:`.

- [ ] **Step 2: Run final pre-PR verification**

Run:

```bash
ruff check src tests
pytest -q
npm test --prefix infra/cloudflare-paper-scheduler
```

Expected: all pass on the same branch head.

- [ ] **Step 3: Review the diff against the approved spec**

Verify explicitly:

- endpoint accepts no trading parameters;
- timing-safe token comparison is used;
- missing server token fails closed;
- HTTP and CLI both call the shared service;
- errors are sanitized at the service boundary;
- Worker never reads response body on failure;
- Worker has no Neon credential;
- GitHub `schedule:` is unchanged;
- live trading remains disabled.

- [ ] **Step 4: Open a draft PR to `main`**

Title:

```text
feat: add Cloudflare paper scheduler path
```

PR body must summarize the shared service, authenticated Render endpoint, Worker, tests, and transitional rollout. It must explicitly say GitHub automatic scheduling remains enabled until Cloudflare production proof. Do not include any secret value.

- [ ] **Step 5: Wait for CI and review evidence**

Require Install, Ruff, full Pytest with PostgreSQL 16, and Cloudflare Worker tests to pass on the exact PR head SHA. Resolve every material review finding before marking Ready.

- [ ] **Step 6: Merge only after fresh GREEN evidence**

Merge with expected head SHA protection. Then verify the `main` CI run is green and Render auto-deploys the merged commit.

- [ ] **Step 7: Verify endpoint is fail-closed before secret configuration**

Call:

```text
POST https://ai-trading-dashboard-qyr2.onrender.com/internal/paper-cycle
```

without Authorization. With no `AI_TRADING_SCHEDULER_TOKEN` configured yet, expected response is sanitized HTTP 503 `scheduler unavailable`. Confirm Render remains dashboard-only and Neon state has not been mutated by the unauthorized request.

---

### Task 5: Manual Cloudflare Boundary and First Production Schedule Proof

This task contains the only required user-operated Cloudflare setup because no Cloudflare connector is available in this ChatGPT environment.

- [ ] **Step 1: Ask the user to create one scheduler token privately**

Give exact instructions to generate at least 32 random bytes encoded as URL-safe text using a password manager or trusted random-secret generator. Explicitly tell the user not to paste the value into ChatGPT.

- [ ] **Step 2: Ask the user to put the same token into Render**

Render dashboard path:

```text
ai-trading-dashboard -> Environment -> Add Environment Variable
```

Name:

```text
AI_TRADING_SCHEDULER_TOKEN
```

Value: the private generated token. Save the environment change and allow Render to redeploy.

- [ ] **Step 3: Verify Render after the user's change**

Check that the new deploy becomes `live`, logs still contain `Hosted paper worker: external scheduler enabled`, and an unauthenticated POST now returns HTTP 401 instead of 503. Confirm Neon state remains intact.

- [ ] **Step 4: Ask the user to import the Worker from GitHub in Cloudflare**

Use the current Cloudflare dashboard flow:

```text
Workers & Pages -> Create application -> Import a repository
```

Connect GitHub if required, choose `dbrckk/Ai-trading`, set the root directory to:

```text
infra/cloudflare-paper-scheduler
```

Ensure Worker name is exactly:

```text
ai-trading-paper-scheduler
```

Then select Save and Deploy. The Wrangler file in that directory owns the five-minute Cron Trigger and `TARGET_URL`.

- [ ] **Step 5: Ask the user to add the Cloudflare secret**

Cloudflare path:

```text
Workers & Pages -> ai-trading-paper-scheduler -> Settings -> Variables and Secrets -> Add
```

Select type `Secret`.

Name:

```text
SCHEDULER_TOKEN
```

Value: the same private token stored in Render. Deploy the secret change. The user must not send the token to ChatGPT.

- [ ] **Step 6: Ask the user to confirm the Cron Trigger exists**

Cloudflare path:

```text
Workers & Pages -> ai-trading-paper-scheduler -> Settings -> Triggers -> Cron Triggers
```

Expected configured cron:

```text
*/5 * * * *
```

Because the Worker is Wrangler-managed, do not create a duplicate second cron entry manually if the Wrangler cron is already present.

- [ ] **Step 7: Observe one real Cloudflare scheduled execution**

After the user reports configuration complete, use Neon as the source of truth. Record before/after:

- runtime key;
- revision;
- `last_processed`;
- `processed_bars`;
- model checksum or stable model metadata;
- `paper_runtime_status.updated_at_utc`;
- engine status.

A proof is valid when a fresh scheduled window advances the durable heartbeat through the Render endpoint. It is acceptable for revision and processed-bar count to remain unchanged when there is no new eligible market bar, as long as the heartbeat is refreshed by the authenticated production cycle.

Also verify Render logs still say `external scheduler enabled`. Do not claim stable scheduling until this scheduled heartbeat proof exists.

- [ ] **Step 8: Update issue #19 with the Cloudflare proof but keep it open**

Document the successful Cloudflare scheduled invocation and state continuity. State that the final acceptance item is removing GitHub automatic scheduling and observing a second Cloudflare invocation afterward.

---

### Task 6: Cut Over GitHub Actions to Manual Fallback Only

**Files:**
- Modify: `.github/workflows/paper-cycle.yml`
- Modify: `tests/test_paper_cycle_workflow.py`
- Modify: `README.md`

This is a separate post-proof PR. Do not start it until Task 5 has a verified Cloudflare scheduled heartbeat.

- [ ] **Step 1: Write RED workflow test**

Change `tests/test_paper_cycle_workflow.py` so required content includes `workflow_dispatch:`, the durable DB secret reference, the DB preflight, and the exact production manual command, while forbidden content includes:

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

Expected: FAIL because the production workflow still contains `schedule:` and `cron:`.

- [ ] **Step 2: Remove only GitHub automatic scheduling**

Change workflow trigger to:

```yaml
on:
  workflow_dispatch:
```

Keep permissions, concurrency, Python setup, `AI_TRADING_DATABASE_URL`, durable DB preflight, install step, and exact `ai-trading paper-cycle --symbol GC=F --period 5d --interval 5m --max-catchup-bars 12` command unchanged.

- [ ] **Step 3: Update README to final production architecture**

Replace the GitHub-every-five-minutes diagram with:

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

Document that GitHub Actions `workflow_dispatch` remains the independent manual fallback. Document `AI_TRADING_SCHEDULER_TOKEN` by variable name only and never include its value.

- [ ] **Step 4: Verify the cutover PR GREEN**

Run:

```bash
pytest tests/test_paper_cycle_workflow.py tests/test_scheduler_endpoint.py tests/test_paper_cycle_service.py tests/test_paper_cycle_cli.py -q
ruff check src tests
pytest -q
npm test --prefix infra/cloudflare-paper-scheduler
```

Expected: all pass.

- [ ] **Step 5: Open, review, and merge the cutover PR**

Use title:

```text
ops: make Cloudflare the paper scheduler
```

The PR body must include the evidence from the first real Cloudflare scheduled heartbeat. Merge only after fresh CI GREEN on the exact head SHA.

- [ ] **Step 6: Verify `main` and Render after cutover**

Confirm `main` CI green, Render live, `AI_TRADING_EXTERNAL_SCHEDULER=1` still active, and no GitHub Actions run with `event=schedule` is expected anymore because the schedule has been removed intentionally.

---

### Task 7: Second Cloudflare Proof and Production Closure

**Files/Systems:**
- Neon production tables
- Render logs and deployment status
- GitHub issue #19
- Cloudflare configuration only through user-visible account setup already completed in Task 5

- [ ] **Step 1: Observe another Cloudflare scheduled heartbeat after GitHub schedule removal**

Use Neon `paper_runtime_status.updated_at_utc` and durable runtime state to prove a new scheduled invocation reached the same runtime after Task 6 merged.

- [ ] **Step 2: Verify continuity and safety**

Confirm:

- runtime key is still `paper:GC=F:5m:online-river:v1`;
- durable revision never decreases;
- `processed_bars` never decreases;
- model remains present;
- no duplicate logical trade/audit commit appears for one execution bar;
- dashboard reports a fresh RUNNING executor after the heartbeat;
- Render logs still report `Hosted paper worker: external scheduler enabled`;
- no live broker route or real-money credential exists.

- [ ] **Step 3: Verify manual fallback still works structurally**

Inspect `.github/workflows/paper-cycle.yml` and confirm `workflow_dispatch` plus the database preflight remain. Do not trigger it merely for ceremony if Cloudflare production is healthy; concurrent execution is safe, but unnecessary production actions should be avoided.

- [ ] **Step 4: Close issue #19**

Update the issue with final production evidence: Cloudflare Worker name, five-minute cron expression, two observed scheduled heartbeats separated by the GitHub cutover, Render dashboard-only state, Neon continuity, and manual GitHub fallback. Then close the issue as completed.

- [ ] **Step 5: Final verification before completion claim**

Use fresh evidence from:

```bash
ruff check src tests
pytest -q
npm test --prefix infra/cloudflare-paper-scheduler
```

plus current `main` CI success, current Render `live` status, and current Neon runtime/status continuity. Only then report the production scheduler as stable.

---

## Rollback Procedure

If Cloudflare scheduling fails after cutover:

1. user disables the Cloudflare Cron Trigger;
2. Render remains with `AI_TRADING_EXTERNAL_SCHEDULER=1` so no uncontrolled in-process daemon starts;
3. GitHub Actions `workflow_dispatch` is used for manual one-shot execution while diagnosing;
4. restoring a GitHub automatic `schedule:` requires a reviewed code change and RED/GREEN workflow test;
5. Neon runtime/model/trade/audit state is not rolled back because scheduler replacement owns no durable trading state.

## Definition of Done

All of these must be true at the same time:

- shared CLI/HTTP execution service has one durable status/error path;
- unauthenticated or misconfigured scheduler endpoint fails closed;
- scheduler token never appears in Git, logs, responses, issue text, or chat;
- Cloudflare Worker contains no trading logic or database credential;
- Worker tests run in CI;
- one real Cloudflare cron invocation is proven before GitHub automatic scheduling is removed;
- GitHub workflow retains manual `workflow_dispatch` but no automatic schedule after cutover;
- a second real Cloudflare cron invocation is proven after that cutover;
- Neon state/model continuity remains intact;
- Render stays dashboard-only;
- dashboard freshness accurately represents missed scheduler heartbeats;
- full Python and Worker test suites are green;
- issue #19 is updated and closed only after production evidence is complete;
- live trading remains disabled.
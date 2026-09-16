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

Add a `STARTING` status-write failure test. Assert the runner factory is never called and the raised service error is `storage_unavailable`.

Add a runner-failure test. Assert best-effort durable `ERROR` is written with `error == "RuntimeError: worker failure"`, then `PaperCycleServiceError.code == "execution_failed"` is raised without the original message or chained secret-bearing exception.

Add a failure test where saving `ERROR` itself raises. Assert the service still raises only the sanitized `PaperCycleServiceError` and does not replace it with the status-store exception.

- [ ] **Step 2: Verify RED**

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

The function must follow this exact failure boundary:

1. reject `max_catchup_bars < 1` before state mutation;
2. construct the backend only when `persistence is None`; backend-construction failure -> `PaperCycleServiceError(code="storage_unavailable", error_type=type(exc).__name__) from None`;
3. write `STARTING` in its own guarded block; failure -> the same `storage_unavailable` service error and no runner call;
4. run the remaining cycle work in a second guarded block;
5. call `runner_factory(backend).run_once()` with exactly `symbol`, `period`, `interval`, and `max_catchup_bars`;
6. load durable state after the runner finishes;
7. calculate equity as `state.cash + state.units * state.last_price`;
8. write `RUNNING` using `result.last_processed`, `result.processed > 0`, `result.reason`, durable units, durable processed-bar count, and `settings.poll_seconds`;
9. return the unchanged `PaperCycleResult`;
10. if the second guarded block fails, make one best-effort `ERROR` status write with sanitized `error=f"{type(exc).__name__}: worker failure"`, then raise `PaperCycleServiceError(code="execution_failed", error_type=type(exc).__name__) from None`.

- [ ] **Step 4: Verify the service GREEN**

```bash
pytest tests/test_paper_cycle_service.py tests/test_paper_cycle.py -q
ruff check src/ai_trading/paper_cycle_service.py tests/test_paper_cycle_service.py
```

Expected: PASS.

- [ ] **Step 5: Refactor the CLI into a thin adapter**

First update `tests/test_paper_cycle_cli.py` so it monkeypatches `command_app.run_production_paper_cycle`. The success test must assert the adapter builds:

```python
ProductionPaperCycleSettings(
    symbol="GC=F",
    period="5d",
    interval="5m",
    max_catchup_bars=12,
    poll_seconds=300.0,
)
```

The failure test must raise:

```python
PaperCycleServiceError(code="execution_failed", error_type="RuntimeError")
```

and assert non-zero CLI exit with no provider detail. Run the updated test before production code and confirm RED.

Then replace `command_app.paper_cycle()` orchestration with one `run_production_paper_cycle(settings)` call. Catch only `PaperCycleServiceError`, print a generic message containing `code` and `error_type`, and raise `typer.Exit(code=1) from None`.

- [ ] **Step 6: Verify CLI and service GREEN**

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
- `handle_scheduler_request()` maps authorization and service result to a sanitized HTTP response.
- Route: `POST /internal/paper-cycle`.
- Credential: `AI_TRADING_SCHEDULER_TOKEN` on Render.
- Executor: shared `run_production_paper_cycle()` using the dashboard's already-constructed persistence backend.

- [ ] **Step 1: Write RED pure endpoint tests**

Create `tests/test_scheduler_endpoint.py` covering:

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

Also cover wrong Bearer token, concurrent-progress result with `processed=0` returning 200, `storage_unavailable` mapping to 503, and `execution_failed` mapping to 500. Assert failure payloads contain no token, database URL, host, original provider message, or `error_type`.

- [ ] **Step 2: Verify RED**

```bash
pytest tests/test_scheduler_endpoint.py -q
```

Expected: collection fails because `ai_trading.scheduler_endpoint` does not exist.

- [ ] **Step 3: Implement the pure adapter**

Create:

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

`handle_scheduler_request()` order:

1. empty configured token -> 503 and no executor call;
2. missing/wrong Authorization -> 401 and no executor call;
3. valid token -> executor exactly once;
4. success -> 200 with only `ok`, integer `processed`, and `status="RUNNING"`;
5. service `storage_unavailable` -> 503 `{"ok": False, "error": "storage unavailable"}`;
6. other `PaperCycleServiceError` -> 500 `{"ok": False, "error": "worker failure"}`.

Do not catch arbitrary exceptions here; the shared service owns runtime-error sanitization and durable `ERROR` reporting.

- [ ] **Step 4: Verify pure adapter GREEN**

```bash
pytest tests/test_scheduler_endpoint.py -q
ruff check src/ai_trading/scheduler_endpoint.py tests/test_scheduler_endpoint.py
```

Expected: PASS.

- [ ] **Step 5: Write RED HTTP integration tests**

Use `serve_dashboard()` test injection arguments:

```python
scheduler_token="server-secret"
paper_cycle_executor=fake_cycle
```

Use `urllib.request.Request` with method POST. Assert missing auth 401, wrong token 401, valid token 200 and one executor call, JSON body with `symbol=SI=F` and `interval=1m` cannot alter executor inputs, `POST /api/status` returns 404, and secret-looking service failures never enter responses.

- [ ] **Step 6: Verify HTTP integration RED**

```bash
pytest tests/test_scheduler_endpoint.py tests/test_dashboard_health.py -q
```

Expected: FAIL because `serve_dashboard()` has no scheduler POST path/injection yet.

- [ ] **Step 7: Wire `dashboard.py`**

Extend `serve_dashboard()` with:

```python
scheduler_token: str | None = None,
paper_cycle_executor: Callable[[], PaperCycleResult] | None = None,
```

Resolve:

```python
effective_scheduler_token = (
    scheduler_token
    if scheduler_token is not None
    else os.getenv("AI_TRADING_SCHEDULER_TOKEN", "").strip()
)
```

If no injected executor exists, create a closure calling `run_production_paper_cycle()` with the existing `backend` and:

```python
ProductionPaperCycleSettings(
    symbol=effective_settings.symbol,
    period=effective_settings.period,
    interval=effective_settings.interval,
    max_catchup_bars=12,
    poll_seconds=300.0,
)
```

Change `_send_json` to accept `status_code: int = 200`. Add `do_POST()` that uses only `urlsplit(self.path).path.rstrip("/")`; exact path `/internal/paper-cycle` calls `handle_scheduler_request()`. Do not parse request body/query for trading configuration. Other POST paths return 404. Keep `log_message()` suppressed.

- [ ] **Step 8: Verify endpoint GREEN**

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
- Public Cloudflare variable `TARGET_URL`.
- Cloudflare secret `SCHEDULER_TOKEN`.
- UTC cron `*/5 * * * *`.
- Target `https://ai-trading-dashboard-qyr2.onrender.com/internal/paper-cycle`.

- [ ] **Step 1: Write Worker tests first**

Create package metadata:

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

Create `test/index.test.js` to assert a fake fetch receives target URL, POST, Bearer header, fixed User-Agent, and no body. Add missing `TARGET_URL` and missing `SCHEDULER_TOKEN` tests that assert no fetch occurs and error is exactly `scheduler configuration missing`. Add non-2xx HTTP 503 test asserting exact error `paper cycle failed with HTTP 503` without token or response-body content. Add a scheduled-handler test that captures and awaits `ctx.waitUntil()` while restoring `globalThis.fetch` in `finally`.

- [ ] **Step 2: Verify Worker RED**

```bash
npm test --prefix infra/cloudflare-paper-scheduler
```

Expected: FAIL because `src/index.js` does not exist.

- [ ] **Step 3: Implement Worker**

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

Do not read response body or log secrets.

- [ ] **Step 4: Add Wrangler config**

```toml
name = "ai-trading-paper-scheduler"
main = "src/index.js"
compatibility_date = "2026-09-16"

[triggers]
crons = ["*/5 * * * *"]

[vars]
TARGET_URL = "https://ai-trading-dashboard-qyr2.onrender.com/internal/paper-cycle"
```

Never put `SCHEDULER_TOKEN` in this file.

- [ ] **Step 5: Document deployment**

`infra/cloudflare-paper-scheduler/README.md` must document exact Worker name, root directory `infra/cloudflare-paper-scheduler`, non-secret `TARGET_URL`, secret binding name `SCHEDULER_TOKEN`, Wrangler-owned cron, no database credential, no trading parameters, and rollback by disabling cron while retaining GitHub manual fallback.

- [ ] **Step 6: Verify Worker GREEN**

```bash
npm test --prefix infra/cloudflare-paper-scheduler
```

Expected: PASS.

- [ ] **Step 7: Add Worker tests to CI**

Add:

```yaml
      - uses: actions/setup-node@v4
        with:
          node-version: "22"
```

and after Pytest:

```yaml
      - name: Cloudflare Worker tests
        run: npm test --prefix infra/cloudflare-paper-scheduler
```

No npm install step is needed because tests use Node built-ins only.

- [ ] **Step 8: Full verification and secret scan**

```bash
npm test --prefix infra/cloudflare-paper-scheduler
ruff check src tests
pytest -q
```

Search committed content for `postgresql://`, plaintext scheduler-token assignments, and secret-looking authorization literals. `Authorization: Bearer` may exist only as source code constructing the header, never followed by a real token value.

- [ ] **Step 9: Commit Task 3**

```bash
git add infra/cloudflare-paper-scheduler .github/workflows/ci.yml
git commit -m "feat: add Cloudflare paper scheduler worker"
```

---

### Task 4: First PR, Review, Merge, and Render Endpoint Deployment

Do not modify `.github/workflows/paper-cycle.yml` yet and do not claim Cloudflare is live in the main README.

- [ ] **Step 1: Prove GitHub fallback is still intact**

```bash
pytest tests/test_paper_cycle_workflow.py -q
```

Inspect workflow and confirm current `schedule:` plus `workflow_dispatch:` are both still present.

- [ ] **Step 2: Fresh full verification**

```bash
ruff check src tests
pytest -q
npm test --prefix infra/cloudflare-paper-scheduler
```

Expected: all pass on one exact head SHA.

- [ ] **Step 3: Review against spec**

Confirm endpoint has no request-controlled trading settings, timing-safe token comparison, missing-token fail-closed behavior, shared CLI/HTTP service, sanitized errors, Worker no response-body logging, Worker no Neon credential, GitHub schedule unchanged, and no live trading route.

- [ ] **Step 4: Open draft PR**

Title `feat: add Cloudflare paper scheduler path`. Body states GitHub automatic scheduling remains during transition. Do not include secrets.

- [ ] **Step 5: Require PR CI GREEN, review, then merge with expected head SHA**

Require Python install, Ruff, full Pytest/PostgreSQL 16, and Worker tests. Resolve material review findings first. After merge, require `main` CI GREEN and Render auto-deploy `live`.

- [ ] **Step 6: Verify pre-secret fail-closed endpoint**

Unauthenticated POST to `https://ai-trading-dashboard-qyr2.onrender.com/internal/paper-cycle` must return sanitized 503 while `AI_TRADING_SCHEDULER_TOKEN` is absent. Verify Neon state is unchanged by the rejected request and Render remains dashboard-only.

---

### Task 5: Manual Cloudflare Boundary and First Production Schedule Proof

This is the user-operated boundary because no Cloudflare connector exists in this environment.

- [ ] **Step 1: User privately creates one scheduler token**

Instruct the user to generate at least 32 random bytes as URL-safe text in a password manager or trusted local generator. Tell them explicitly not to paste it into ChatGPT.

- [ ] **Step 2: User configures Render**

Path:

```text
ai-trading-dashboard -> Environment -> Add Environment Variable
```

Name `AI_TRADING_SCHEDULER_TOKEN`; value is the private generated token. Save and redeploy.

- [ ] **Step 3: Assistant verifies Render and unauthenticated rejection**

Require new deploy `live`, `Hosted paper worker: external scheduler enabled` in logs, unauthenticated POST now 401, and intact Neon state.

- [ ] **Step 4: User verifies one authorized endpoint call without revealing token**

If a local shell is available, use:

```bash
export SCHEDULER_TOKEN='value stored in your password manager'
curl -i -X POST \
  -H "Authorization: Bearer ${SCHEDULER_TOKEN}" \
  https://ai-trading-dashboard-qyr2.onrender.com/internal/paper-cycle
unset SCHEDULER_TOKEN
```

Expected HTTP status is 200 with a small JSON payload containing `ok`, `processed`, and `status`. The user reports only the HTTP status and non-secret JSON fields, never the token. If no local shell is available, use a trusted local HTTP client on the user's device with the same method, URL, and Authorization header; do not use a public request-sharing website.

After the user's report, verify Neon heartbeat/state changed or safely no-op'd with a fresh heartbeat.

- [ ] **Step 5: User imports Worker from GitHub into Cloudflare**

Current dashboard path:

```text
Workers & Pages -> Create application -> Import a repository
```

Connect GitHub if required, choose `dbrckk/Ai-trading`, root directory `infra/cloudflare-paper-scheduler`, Worker name exactly `ai-trading-paper-scheduler`, then Save and Deploy.

- [ ] **Step 6: User adds Cloudflare secret**

Path:

```text
Workers & Pages -> ai-trading-paper-scheduler -> Settings -> Variables and Secrets -> Add
```

Type `Secret`, name `SCHEDULER_TOKEN`, value the same private token used on Render. Deploy the secret change. Do not send the token to ChatGPT.

- [ ] **Step 7: User confirms Cron Trigger**

Path:

```text
Workers & Pages -> ai-trading-paper-scheduler -> Settings -> Triggers -> Cron Triggers
```

Expected `*/5 * * * *`. Since Wrangler owns it, do not add a duplicate cron if already present.

- [ ] **Step 8: Observe one real Cloudflare scheduled execution**

Use Neon before/after evidence: runtime key, revision, last_processed, processed_bars, model metadata/checksum, `paper_runtime_status.updated_at_utc`, engine status. A fresh scheduled heartbeat is sufficient even when there is no new market bar and revision does not advance. Verify Render still logs external scheduler mode.

- [ ] **Step 9: Update issue #19 but keep it open**

Record first Cloudflare scheduled proof and state continuity. Remaining item is GitHub automatic-schedule removal plus a second Cloudflare proof.

---

### Task 6: Cut Over GitHub Actions to Manual Fallback Only

**Files:**
- Modify: `.github/workflows/paper-cycle.yml`
- Modify: `tests/test_paper_cycle_workflow.py`
- Modify: `README.md`

Do not start before Task 5 has real Cloudflare scheduled-heartbeat evidence.

- [ ] **Step 1: Write RED workflow test**

Change forbidden strings to include:

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

Required content remains `workflow_dispatch:`, DB secret reference, DB preflight, concurrency guard, and exact manual paper-cycle command.

```bash
pytest tests/test_paper_cycle_workflow.py -q
```

Expected: FAIL because current workflow still has automatic schedule.

- [ ] **Step 2: Remove only GitHub automatic schedule**

Use:

```yaml
on:
  workflow_dispatch:
```

Keep all job behavior unchanged.

- [ ] **Step 3: Update README to final architecture**

Use diagram:

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

Document GitHub `workflow_dispatch` as manual fallback and mention `AI_TRADING_SCHEDULER_TOKEN` by name only.

- [ ] **Step 4: Verify cutover GREEN**

```bash
pytest tests/test_paper_cycle_workflow.py tests/test_scheduler_endpoint.py tests/test_paper_cycle_service.py tests/test_paper_cycle_cli.py -q
ruff check src tests
pytest -q
npm test --prefix infra/cloudflare-paper-scheduler
```

Expected: PASS.

- [ ] **Step 5: Open/review/merge second PR**

Title `ops: make Cloudflare the paper scheduler`. PR body includes first Cloudflare scheduled evidence. Merge only after exact-head CI GREEN.

- [ ] **Step 6: Verify `main` and Render after cutover**

Require main CI GREEN, Render live, external scheduler mode still enabled, and confirm GitHub workflow now intentionally has no automatic schedule.

---

### Task 7: Second Cloudflare Proof and Production Closure

- [ ] **Step 1: Observe another Cloudflare heartbeat after GitHub schedule removal**

Use Neon `paper_runtime_status.updated_at_utc` and durable state to prove another scheduled invocation reached the same runtime.

- [ ] **Step 2: Verify continuity and safety**

Confirm stable runtime key, nondecreasing revision and processed_bars, model present, no duplicate logical trade/audit commit for one execution bar, dashboard fresh RUNNING status, Render external scheduler log, and no live broker route/credential.

- [ ] **Step 3: Verify GitHub manual fallback structurally**

Confirm `workflow_dispatch` and durable DB preflight remain. Do not run a redundant production cycle merely for ceremony.

- [ ] **Step 4: Update and close issue #19**

Record Worker name, cron expression, two observed Cloudflare scheduled heartbeats separated by GitHub cutover, Render dashboard-only state, Neon continuity, and GitHub manual fallback. Close as completed.

- [ ] **Step 5: Fresh final verification before completion claim**

```bash
ruff check src tests
pytest -q
npm test --prefix infra/cloudflare-paper-scheduler
```

Also require current main CI success, current Render live status, and current Neon continuity evidence before reporting stable production scheduling.

---

## Rollback Procedure

If Cloudflare scheduling fails after cutover:

1. user disables the Cloudflare Cron Trigger;
2. Render remains `AI_TRADING_EXTERNAL_SCHEDULER=1`;
3. GitHub `workflow_dispatch` provides manual one-shot execution;
4. restoring GitHub automatic scheduling requires a reviewed RED/GREEN code change;
5. Neon runtime/model/trade/audit state is not rolled back because scheduler replacement owns no durable trading state.

## Definition of Done

- CLI and HTTP share one durable production-cycle service.
- Unauthorized or misconfigured scheduler endpoint fails closed.
- Scheduler token never appears in Git, logs, responses, issue text, or chat.
- Cloudflare Worker contains no trading logic or DB credential and fails closed on missing bindings.
- Worker tests run in CI.
- One real Cloudflare cron invocation is proven before GitHub automatic scheduling is removed.
- GitHub retains `workflow_dispatch` but no automatic schedule after cutover.
- A second Cloudflare cron invocation is proven after cutover.
- Neon state/model continuity remains intact.
- Render remains dashboard-only.
- Dashboard freshness reflects scheduler heartbeat failures.
- Python and Worker test suites are green.
- Issue #19 closes only after production evidence is complete.
- Live trading remains disabled.
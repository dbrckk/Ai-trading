# Continuous Paper Execution Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Run the paper executor independently of Render every 5 minutes, catch up missed eligible bars safely, and share one durable Neon PostgreSQL state with the Render dashboard.

**Architecture:** Keep `PaperAutonomousRuntime` as the only trading/risk execution path, add deterministic targeted-bar execution plus a focused `PaperCycleRunner`, expose it through `ai-trading paper-cycle`, and schedule that command with GitHub Actions. Render becomes dashboard-only when `AI_TRADING_EXTERNAL_SCHEDULER=1`; Neon is consumed through the existing generic PostgreSQL backend and `AI_TRADING_DATABASE_URL` contract.

**Tech Stack:** Python 3.11+, pandas, Typer, psycopg 3, River/joblib, PostgreSQL 16-compatible Neon, GitHub Actions, Render, pytest, Ruff.

**Spec:** `docs/superpowers/specs/2026-09-16-continuous-paper-execution-design.md`

## Global Constraints

- Paper trading only; do not add a live broker adapter, live brokerage credential, or real-order route.
- Keep `RiskEngine` mandatory before every paper rebalance.
- Stable production runtime key is `paper:{symbol}:{interval}:online-river:v1`, built only by `build_runtime_key()`.
- `AI_TRADING_DATABASE_URL` selects PostgreSQL; when configured and unavailable, fail closed with no file fallback.
- GitHub Actions production cadence is `*/5 * * * *`; sub-5-minute scheduling is out of scope.
- Fresh runtime processes only the latest eligible execution bar; it never replays the downloaded history as backlog.
- Existing runtime catches up missed eligible execution bars oldest-first, maximum 12 by default per invocation.
- If `last_processed` predates the earliest execution bar reconstructable from the loaded history, fail closed instead of silently skipping backlog.
- Each caught-up bar is its own atomic PostgreSQL state/model/trade/audit commit.
- Revision conflict discards local losing state/model, reloads durable state, and resumes only if budget remains.
- External scheduling is explicit via `AI_TRADING_EXTERNAL_SCHEDULER=1`; do not infer it from database presence.
- Database URLs/passwords must never be committed, logged, placed in issue/PR text, or returned by dashboard APIs.
- Production dashboard and executor must use the same Neon database and runtime key.
- Do not delete the temporary Render PostgreSQL instance without explicit user approval.

---

### Task 1: Deterministic Targeted Runtime Step

**Files:**
- Modify: `src/ai_trading/runtime.py`
- Modify: `tests/test_runtime.py`
- Create: `tests/test_runtime_targeted_step.py`

**Interfaces:**
- Consumes: `PaperPersistence.load_runtime()`, `PaperPersistence.commit_step()`, `RuntimeStepResult`.
- Produces: `PaperAutonomousRuntime.step_at(df: pd.DataFrame, execution_idx: object) -> RuntimeStepResult`, `_eligible_execution_indices(df: pd.DataFrame) -> tuple[object, ...]`, and one shared execution implementation used by both `step()` and `step_at()`.

- [ ] **Step 1: Write failing targeted-step tests**

Create `tests/test_runtime_targeted_step.py` with concrete local helpers:

```python
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from ai_trading.audit import AuditLog
from ai_trading.config import RiskConfig
from ai_trading.runtime import PaperAutonomousRuntime
from ai_trading.runtime_state import RuntimeStateStore


def sample_market(n: int = 105) -> pd.DataFrame:
    idx = pd.date_range("2025-01-01", periods=n, freq="5min")
    t = np.arange(n, dtype=float)
    close = 100.0 + 0.1 * t + 2.0 * np.sin(t / 5.0)
    open_ = close * (1.0 + 0.001 * np.sin(t / 3.0))
    return pd.DataFrame(
        {
            "Open": open_,
            "High": np.maximum(open_, close) * 1.005,
            "Low": np.minimum(open_, close) * 0.995,
            "Close": close,
            "Volume": 1000.0 + t,
        },
        index=idx,
    )


def build_file_runtime(tmp_path: Path) -> PaperAutonomousRuntime:
    return PaperAutonomousRuntime(
        risk_config=RiskConfig(min_confidence=0.0),
        state_store=RuntimeStateStore(tmp_path / "state.json"),
        audit_log=AuditLog(tmp_path / "audit.jsonl"),
        online_model_path=tmp_path / "online.joblib",
        lock_path=tmp_path / "runtime.lock",
        symbol="GC=F",
    )


def test_step_at_processes_requested_execution_bar(tmp_path: Path) -> None:
    df = sample_market()
    runtime = build_file_runtime(tmp_path)
    target = runtime._eligible_execution_indices(df)[-3]

    result = runtime.step_at(df, target)

    assert result.processed is True
    assert result.timestamp == str(target)


def test_step_at_is_idempotent_for_same_execution_bar(tmp_path: Path) -> None:
    df = sample_market()
    runtime = build_file_runtime(tmp_path)
    target = runtime._eligible_execution_indices(df)[-2]

    first = runtime.step_at(df, target)
    second = runtime.step_at(df, target)

    assert first.processed is True
    assert second.processed is False
    assert second.reason == "bar already processed"


def test_step_at_rejects_non_eligible_execution_bar(tmp_path: Path) -> None:
    df = sample_market()
    runtime = build_file_runtime(tmp_path)

    with pytest.raises(ValueError, match="eligible execution bar"):
        runtime.step_at(df, df.index[0])
```

- [ ] **Step 2: Run targeted tests and verify RED**

```bash
pytest tests/test_runtime.py tests/test_runtime_targeted_step.py -q
```

Expected: FAIL because `step_at()` and `_eligible_execution_indices()` do not exist.

- [ ] **Step 3: Refactor runtime to one shared execution path**

Implement these concrete method boundaries in `PaperAutonomousRuntime`:

```python
def _eligible_execution_indices(self, df: pd.DataFrame) -> tuple[object, ...]:
    features = make_features(df)
    valid = features.dropna().index
    execution: list[object] = []
    for signal_idx in valid:
        signal_pos = int(df.index.get_loc(signal_idx))
        if signal_pos + 1 < len(df.index):
            execution.append(df.index[signal_pos + 1])
    return tuple(dict.fromkeys(execution))


def step(self, df: pd.DataFrame) -> RuntimeStepResult:
    eligible = self._eligible_execution_indices(df)
    if not eligible:
        raise ValueError("No eligible execution bar available")
    return self.step_at(df, eligible[-1])


def step_at(self, df: pd.DataFrame, execution_idx: object) -> RuntimeStepResult:
    eligible = self._eligible_execution_indices(df)
    if execution_idx not in eligible:
        raise ValueError("Requested index is not an eligible execution bar")
    return self._step_at_locked(df, execution_idx)
```

`_step_at_locked()` must contain the existing state/model/prediction/risk/broker/trade/audit/commit behavior. Derive `signal_idx` from the dataframe row immediately preceding `execution_idx`, then verify that signal index is one of the valid feature indices before using it. Keep existing reason strings and persistence conflict behavior unchanged.

- [ ] **Step 4: Verify targeted and legacy behavior GREEN**

```bash
pytest tests/test_runtime.py tests/test_runtime_targeted_step.py tests/test_runtime_persistence.py -q
ruff check src/ai_trading/runtime.py tests/test_runtime.py tests/test_runtime_targeted_step.py
```

Expected: PASS.

- [ ] **Step 5: Commit Task 1**

```bash
git add src/ai_trading/runtime.py tests/test_runtime.py tests/test_runtime_targeted_step.py
git commit -m "refactor: support targeted paper runtime steps"
```

---

### Task 2: One-Shot Catch-Up Runner

**Files:**
- Create: `src/ai_trading/paper_cycle.py`
- Create: `tests/test_paper_cycle.py`
- Modify: `tests/test_postgres_persistence.py`

**Interfaces:**
- Consumes: `build_runtime_key(symbol, interval)`, `PaperPersistence`, `PaperAutonomousRuntime.step_at()`, `PaperAutonomousRuntime._eligible_execution_indices()`, and an injected market-data loader.
- Produces:

```python
@dataclass(frozen=True)
class PaperCycleResult:
    processed: int
    remaining_backlog: bool
    last_processed: str | None
    processed_bars: int
    reason: str
```

and a `PaperCycleRunner` with constructor arguments `persistence`, `data_loader`, and `runtime_factory`, plus `run_once(symbol, period, interval, max_catchup_bars=12) -> PaperCycleResult`.

- [ ] **Step 1: Write RED tests for fresh-run, backlog, cap, history-gap, and conflict semantics**

Create tests with a fake runtime recording requested targets and a fake persistence that returns `PersistedRuntime` snapshots. The assertions must be concrete:

```python
def test_fresh_runtime_processes_only_latest_eligible_bar() -> None:
    result = runner.run_once(symbol="GC=F", period="5d", interval="5m", max_catchup_bars=12)
    assert seen_targets == [eligible[-1]]
    assert result.processed == 1
    assert result.remaining_backlog is False


def test_existing_runtime_catches_up_oldest_first() -> None:
    result = runner.run_once(symbol="GC=F", period="5d", interval="5m", max_catchup_bars=12)
    assert seen_targets == [eligible[-4], eligible[-3], eligible[-2], eligible[-1]]
    assert result.processed == 4


def test_catchup_cap_leaves_remaining_backlog() -> None:
    result = runner.run_once(symbol="GC=F", period="5d", interval="5m", max_catchup_bars=2)
    assert len(seen_targets) == 2
    assert result.remaining_backlog is True


def test_missing_last_processed_in_history_fails_closed() -> None:
    with pytest.raises(RuntimeError, match="persisted last_processed is outside loaded history"):
        runner.run_once(symbol="GC=F", period="5d", interval="5m", max_catchup_bars=12)


def test_no_new_bar_is_healthy_and_idempotent() -> None:
    result = runner.run_once(symbol="GC=F", period="5d", interval="5m", max_catchup_bars=12)
    assert result.processed == 0
    assert result.remaining_backlog is False
    assert result.reason == "no new eligible bar"
```

Add a conflict test where the first fake `step_at()` returns `processed=False, reason="persistence revision conflict"`, persistence then reports that another writer advanced `last_processed`, and the runner recomputes targets without reprocessing that bar.

- [ ] **Step 2: Run runner tests and verify RED**

```bash
pytest tests/test_paper_cycle.py -q
```

Expected: FAIL because `ai_trading.paper_cycle` does not exist.

- [ ] **Step 3: Implement bounded catch-up**

Use this exact selection algorithm:

```python
runtime_key = build_runtime_key(symbol, interval)
runtime = self.runtime_factory(
    symbol=symbol,
    persistence=self.persistence,
    runtime_key=runtime_key,
)
df = self.data_loader(symbol, period, interval)
eligible = runtime._eligible_execution_indices(df)
if not eligible:
    raise RuntimeError("market history contains no eligible execution bar")

snapshot = self.persistence.load_runtime(runtime_key, runtime.risk_config.starting_cash)
if snapshot.is_new:
    targets = list(eligible[-1:])
else:
    if snapshot.state.last_processed is None:
        raise RuntimeError("persisted runtime is missing last_processed")
    positions = {str(value): index for index, value in enumerate(eligible)}
    if snapshot.state.last_processed not in positions:
        raise RuntimeError("persisted last_processed is outside loaded history")
    targets = list(eligible[positions[snapshot.state.last_processed] + 1 :])
```

Reject `max_catchup_bars < 1`. Process `targets[:max_catchup_bars]` oldest-first. After every call to `step_at()`, reload durable state and recompute remaining eligible targets from `last_processed`; this is mandatory after a revision conflict. `remaining_backlog` is true only when durable state still has eligible targets newer than `last_processed` after the invocation budget is exhausted.

- [ ] **Step 4: Add PostgreSQL reconstruction integration coverage**

Using `TEST_DATABASE_URL`, construct two separate `PostgresPaperPersistence` objects and two separate `PaperCycleRunner` objects against the same runtime key. Process a multi-bar sequence, reconstruct objects, continue, then assert:

```python
final = second_persistence.load_runtime(runtime_key, 100_000.0)
assert final.state.processed_bars >= 2
assert final.revision == final.state.processed_bars
assert final.state.last_processed == str(expected_latest_execution_bar)
assert final.model is not None
```

Keep the existing forced-failure transaction test and assert state/model/trade/audit remain unchanged after rollback.

- [ ] **Step 5: Verify Task 2 GREEN**

```bash
pytest tests/test_paper_cycle.py tests/test_postgres_persistence.py -q
ruff check src/ai_trading/paper_cycle.py tests/test_paper_cycle.py tests/test_postgres_persistence.py
```

Expected: PASS.

- [ ] **Step 6: Commit Task 2**

```bash
git add src/ai_trading/paper_cycle.py tests/test_paper_cycle.py tests/test_postgres_persistence.py
git commit -m "feat: add bounded paper cycle catch-up runner"
```

---

### Task 3: CLI Command, Durable Status, and Dashboard-Only Hosted Mode

**Files:**
- Modify: `src/ai_trading/cli.py`
- Modify: `src/ai_trading/hosted_runtime.py`
- Modify: `tests/test_hosted_runtime.py`
- Create: `tests/test_paper_cycle_cli.py`

**Interfaces:**
- Consumes: `PaperCycleRunner`, `build_paper_persistence()`, `build_runtime_key()`, `HostedRuntimeStatus`, `HostedPaperSettings`.
- Produces: `ai-trading paper-cycle` and `HostedPaperSettings.external_scheduler: bool`.

- [ ] **Step 1: Write RED external-scheduler test**

Add:

```python
def test_external_scheduler_suppresses_daemon(monkeypatch) -> None:
    monkeypatch.setenv("AI_TRADING_HOSTED_PAPER", "1")
    monkeypatch.setenv("AI_TRADING_EXTERNAL_SCHEDULER", "1")
    settings = HostedPaperSettings.from_env()

    thread = start_hosted_paper_runtime(settings=settings, runner=lambda _: None)

    assert settings.external_scheduler is True
    assert thread is None
```

Keep the existing daemon-start test and explicitly clear `AI_TRADING_EXTERNAL_SCHEDULER` there so backward compatibility is proven.

- [ ] **Step 2: Write RED CLI/status tests**

Use `typer.testing.CliRunner`. Monkeypatch `build_paper_persistence` to return a fake persistence and monkeypatch `PaperCycleRunner` to a fake class with a deterministic `run_once()` result. Assert the command:

```text
paper-cycle --symbol GC=F --period 5d --interval 5m --max-catchup-bars 12
```

writes `STARTING`, invokes the runner with those exact parameters, then writes `RUNNING` with `poll_seconds=300.0`, durable `processed_bars`, equity and units loaded from persistence, and a sanitized reason. Add failure tests proving an executor exception yields non-zero exit, best-effort `ERROR`, and that status persistence failure does not replace the executor exception.

- [ ] **Step 3: Implement hosted flag and CLI**

Add the field:

```python
external_scheduler: bool = False
```

Parse it with:

```python
external_scheduler = os.getenv("AI_TRADING_EXTERNAL_SCHEDULER", "0").strip().lower() in {
    "1",
    "true",
    "yes",
    "on",
}
```

`start_hosted_paper_runtime()` must return `None` when this flag is true and print only `Hosted paper worker: external scheduler enabled`.

Add `@app.command("paper-cycle")`. The command must:

```python
backend = build_paper_persistence()
runtime_key = build_runtime_key(symbol, interval)
backend.save_runtime_status(runtime_key, starting_status)
result = PaperCycleRunner(persistence=backend).run_once(
    symbol=symbol,
    period=period,
    interval=interval,
    max_catchup_bars=max_catchup_bars,
)
state = backend.load_runtime(runtime_key, 100_000.0).state
backend.save_runtime_status(runtime_key, running_status_from_result_and_state)
```

Use `poll_seconds=300.0`. Do not add `last_processed` to `HostedRuntimeStatus`; the dashboard reads it from durable `RuntimeState`. On exceptions, store only `error=f"{type(exc).__name__}: worker failure"`, then re-raise through Typer without printing the exception message.

- [ ] **Step 4: Verify Task 3 GREEN**

```bash
pytest tests/test_hosted_runtime.py tests/test_paper_cycle_cli.py -q
ruff check src/ai_trading/cli.py src/ai_trading/hosted_runtime.py tests/test_hosted_runtime.py tests/test_paper_cycle_cli.py
```

Expected: PASS.

- [ ] **Step 5: Commit Task 3**

```bash
git add src/ai_trading/cli.py src/ai_trading/hosted_runtime.py tests/test_hosted_runtime.py tests/test_paper_cycle_cli.py
git commit -m "feat: add external scheduled paper cycle command"
```

---

### Task 4: Five-Minute GitHub Actions Scheduler

**Files:**
- Create: `.github/workflows/paper-cycle.yml`
- Create: `tests/test_paper_cycle_workflow.py`

**Interfaces:**
- Consumes: `ai-trading paper-cycle`, repository secret `AI_TRADING_DATABASE_URL`.
- Produces: scheduled/manual one-shot production executor.

- [ ] **Step 1: Write RED workflow structure test**

Create a test that reads `.github/workflows/paper-cycle.yml` and asserts these exact strings are present:

```python
required = (
    'cron: "*/5 * * * *"',
    "workflow_dispatch:",
    "group: paper-cycle-production",
    "cancel-in-progress: false",
    "AI_TRADING_DATABASE_URL: ${{ secrets.AI_TRADING_DATABASE_URL }}",
    "ai-trading paper-cycle --symbol GC=F --period 5d --interval 5m --max-catchup-bars 12",
)
```

Assert these secret-like literals are absent:

```python
for forbidden in ("postgresql://", "postgres://", "password="):
    assert forbidden not in text
```

- [ ] **Step 2: Run workflow test and verify RED**

```bash
pytest tests/test_paper_cycle_workflow.py -q
```

Expected: FAIL because the workflow file does not exist.

- [ ] **Step 3: Create production workflow**

Use:

```yaml
name: Paper Cycle

on:
  schedule:
    - cron: "*/5 * * * *"
  workflow_dispatch:

permissions:
  contents: read

concurrency:
  group: paper-cycle-production
  cancel-in-progress: false

jobs:
  paper-cycle:
    runs-on: ubuntu-latest
    timeout-minutes: 10
    env:
      AI_TRADING_DATABASE_URL: ${{ secrets.AI_TRADING_DATABASE_URL }}
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
          cache: pip
      - name: Install
        run: python -m pip install .
      - name: Run paper cycle
        run: ai-trading paper-cycle --symbol GC=F --period 5d --interval 5m --max-catchup-bars 12
```

- [ ] **Step 4: Verify workflow test GREEN**

```bash
pytest tests/test_paper_cycle_workflow.py -q
ruff check tests/test_paper_cycle_workflow.py
```

Expected: PASS.

- [ ] **Step 5: Commit Task 4**

```bash
git add .github/workflows/paper-cycle.yml tests/test_paper_cycle_workflow.py
git commit -m "ci: schedule paper cycle every five minutes"
```

---

### Task 5: Dashboard External-Executor Observability

**Files:**
- Modify: `src/ai_trading/dashboard.py`
- Modify: `tests/test_dashboard.py`
- Modify: `tests/test_dashboard_runtime.py`

**Interfaces:**
- Consumes: durable `RuntimeState`, `HostedRuntimeStatus`, existing `runtime_status_snapshot()`.
- Produces: HTML state metrics `Last processed` and `Processed bars`; no provider/database metadata.

- [ ] **Step 1: Write RED dashboard test**

Use a fake persistence returning:

```python
RuntimeState(
    cash=100_000.0,
    units=0.0,
    last_price=2500.0,
    peak_equity=100_000.0,
    day_start_equity=100_000.0,
    last_processed="2026-09-16 05:20:00+00:00",
    processed_bars=17,
)
```

Assert the page contains `Last processed`, the timestamp, `Processed bars`, and `17`. Add a storage failure fake whose exception text contains `db.internal.example:5432`; assert that hostname is absent from HTML and public JSON.

- [ ] **Step 2: Run dashboard tests and verify RED**

```bash
pytest tests/test_dashboard.py tests/test_dashboard_runtime.py -q
```

Expected: FAIL because the two durable state metrics are not rendered yet.

- [ ] **Step 3: Add state metrics without changing health semantics**

When storage is healthy:

```python
last_processed = state.last_processed if state is not None else None
processed_bars = state.processed_bars if state is not None else None
```

Render `-` when unavailable. Keep `/healthz` status code/JSON semantics and sanitized `storage unavailable` behavior unchanged.

- [ ] **Step 4: Verify dashboard GREEN**

```bash
pytest tests/test_dashboard.py tests/test_dashboard_runtime.py tests/test_dashboard_http.py -q
ruff check src/ai_trading/dashboard.py tests/test_dashboard.py tests/test_dashboard_runtime.py
```

Expected: PASS.

- [ ] **Step 5: Commit Task 5**

```bash
git add src/ai_trading/dashboard.py tests/test_dashboard.py tests/test_dashboard_runtime.py
git commit -m "feat: show durable paper progress in dashboard"
```

---

### Task 6: Full Verification, Neon Rollout, and Continuity Proof

**Files:**
- Modify: `README.md`
- Update: GitHub issue `#19` after proof
- Do not change PostgreSQL schema solely for Neon.

**Interfaces:**
- Consumes: connected Neon integration, Render environment mutation, GitHub Actions repository secret `AI_TRADING_DATABASE_URL`.
- Produces: production Neon database, Render dashboard-only mode, scheduled executor, recorded continuity evidence.

- [ ] **Step 1: Document production operating model**

README must explicitly state:

```text
Render: dashboard only when AI_TRADING_EXTERNAL_SCHEDULER=1
GitHub Actions: paper-cycle every 5 minutes
PostgreSQL: shared durable database selected by AI_TRADING_DATABASE_URL
Production runtime key: paper:GC=F:5m:online-river:v1
```

Document fresh/latest-only initialization, oldest-first catch-up capped at 12 bars/run, and fail-closed behavior when durable `last_processed` is outside loaded history.

- [ ] **Step 2: Run complete verification before PR**

```bash
ruff check src tests
pytest -q
```

Expected: 0 Ruff errors and 0 test failures. In GitHub CI, PostgreSQL integration must run against the existing PostgreSQL 16 service.

- [ ] **Step 3: Open implementation PR and require fresh CI GREEN**

Open PR from the implementation branch to `main`. Do not merge until the PR run shows Install, Ruff, and Pytest all successful and PostgreSQL 16 healthy.

- [ ] **Step 4: Create Neon production project after code/CI approval**

Through Neon:

- create project `ai-trading-paper-production`;
- request PostgreSQL 16;
- choose an available European region when the API exposes one;
- keep the default branch/database as production;
- retrieve the connection string only through `Neon.get_connection_string`;
- never echo the returned value into chat, source, issue text, PR text, or logs.

- [ ] **Step 5: Configure Render with Neon and external scheduling**

Merge these environment variables into the existing service without replacing unrelated values:

```text
AI_TRADING_DATABASE_URL=<Neon secret>
AI_TRADING_EXTERNAL_SCHEDULER=1
AI_TRADING_HOSTED_PAPER=1
AI_TRADING_HOSTED_SYMBOL=GC=F
AI_TRADING_HOSTED_PERIOD=5d
AI_TRADING_HOSTED_INTERVAL=5m
```

The dashboard startup calls `build_paper_persistence()`, whose PostgreSQL factory calls `initialize_schema()`. Therefore this first Neon-backed Render start is the schema initialization path; no separate handwritten DDL migration is needed.

After redeploy, verify Render logs contain `Hosted paper worker: external scheduler enabled` and do not contain `Hosted paper worker: daemon thread started`.

- [ ] **Step 6: Verify Neon schema through read-only SQL**

Use Neon SQL for this read-only catalog check:

```sql
SELECT to_regclass('public.paper_runtime_state') AS runtime_state,
       to_regclass('public.paper_model_state') AS model_state,
       to_regclass('public.paper_trades') AS trades,
       to_regclass('public.paper_audit_events') AS audit_events,
       to_regclass('public.paper_runtime_status') AS runtime_status;
```

All five results must be non-null.

- [ ] **Step 7: Configure GitHub Actions secret or stop at authorization boundary**

Required repository secret:

```text
AI_TRADING_DATABASE_URL=<same Neon secret>
```

If an authorized GitHub secret-write integration exists, set it without revealing the value. If the connector still excludes secret mutation, record this as the single manual owner action and do not expose the secret in chat.

- [ ] **Step 8: Manually dispatch first paper cycle and capture baseline**

After the GitHub secret exists, dispatch `Paper Cycle`. Require success. Query Neon and record only non-secret fields:

```sql
SELECT runtime_key, revision, last_processed, processed_bars
FROM paper_runtime_state
WHERE runtime_key = 'paper:GC=F:5m:online-river:v1';
```

```sql
SELECT format, version, sha256
FROM paper_model_state
WHERE runtime_key = 'paper:GC=F:5m:online-river:v1';
```

```sql
SELECT engine_status, updated_at_utc
FROM paper_runtime_status
WHERE runtime_key = 'paper:GC=F:5m:online-river:v1';
```

- [ ] **Step 9: Prove process/redeploy continuity**

Trigger a Render redeploy without code changes. After Render is live, dispatch another paper cycle. If no newer eligible bar exists, idempotent no-new-bar is acceptable; if a newer eligible bar exists, revision and `processed_bars` must advance.

Re-query Neon and verify:

- runtime key unchanged;
- revision never decreased;
- processed-bar count never decreased;
- model row still present with format/version/checksum;
- runtime status heartbeat refreshed by the executor;
- dashboard reads the same durable state after Render process replacement.

- [ ] **Step 10: Observe scheduled path and close tracking issue only after proof**

Observe at least one schedule-triggered `Paper Cycle` run. Confirm it succeeds and normal overlap is prevented by the workflow concurrency group. Update issue #19 with commit, PR, workflow run IDs and non-secret continuity values. Close #19 only after every acceptance criterion is met.

- [ ] **Step 11: Final production verification**

Require all of:

```text
main CI = success
latest Render deploy = live
Paper Cycle manual run = success
Paper Cycle scheduled run = success
Neon runtime row = present and advancing or idempotently unchanged when no new bar exists
Neon model row = present
Neon status row = present and fresh
Render daemon = suppressed
Dashboard /healthz = reachable
No live brokerage route = introduced
```

The temporary Render Free PostgreSQL instance remains untouched unless the user explicitly approves deletion.

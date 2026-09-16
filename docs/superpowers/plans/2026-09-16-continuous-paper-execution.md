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
- Produces: `PaperAutonomousRuntime.step_at(df: pd.DataFrame, execution_idx: object) -> RuntimeStepResult` and a shared private implementation used by both `step()` and `step_at()`.

- [ ] **Step 1: Write failing targeted-step tests**

```python
from ai_trading.runtime import PaperAutonomousRuntime


def test_step_at_processes_requested_execution_bar(tmp_path) -> None:
    df = sample_market(105)
    runtime = build_file_runtime(tmp_path)
    target = df.index[-4]

    result = runtime.step_at(df, target)

    assert result.processed is True
    assert result.timestamp == str(target)


def test_step_at_rejects_non_eligible_execution_bar(tmp_path) -> None:
    df = sample_market(105)
    runtime = build_file_runtime(tmp_path)

    with pytest.raises(ValueError, match="eligible execution bar"):
        runtime.step_at(df, df.index[0])
```

Also extend the existing idempotence test so calling `step_at(df, target)` twice returns `processed=False` with `reason == "bar already processed"` on the second call.

- [ ] **Step 2: Run targeted tests and verify RED**

Run:

```bash
pytest tests/test_runtime.py tests/test_runtime_targeted_step.py -q
```

Expected: FAIL because `PaperAutonomousRuntime.step_at` does not exist.

- [ ] **Step 3: Refactor `PaperAutonomousRuntime` to one shared execution implementation**

Implement this shape without duplicating the prediction/risk/broker/commit block:

```python
def step(self, df: pd.DataFrame) -> RuntimeStepResult:
    execution_idx = self._latest_eligible_execution_idx(df)
    return self.step_at(df, execution_idx)


def step_at(self, df: pd.DataFrame, execution_idx: object) -> RuntimeStepResult:
    with RuntimeLock(self.lock_path):
        context = self._prepare_execution_context(df, execution_idx)
        return self._execute_context(context)
```

`_prepare_execution_context()` must derive the signal row immediately preceding the requested execution row using the same valid-feature rules as current `step()`. It must reject targets with no valid predecessor, no execution row, or targets outside the dataframe. Keep the existing state/model/trade/audit data and reason strings unchanged where behavior is unchanged.

- [ ] **Step 4: Verify targeted and legacy runtime behavior GREEN**

Run:

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
- Consumes: `build_runtime_key(symbol, interval)`, `PaperPersistence`, `PaperAutonomousRuntime.step_at()`, `load_history()` through injection.
- Produces:

```python
@dataclass(frozen=True)
class PaperCycleResult:
    processed: int
    remaining_backlog: bool
    last_processed: str | None
    processed_bars: int
    reason: str


class PaperCycleRunner:
    def __init__(
        self,
        *,
        persistence: PaperPersistence,
        data_loader: Callable[[str, str, str], pd.DataFrame] = load_history,
        runtime_factory: Callable[..., PaperAutonomousRuntime] = PaperAutonomousRuntime,
    ) -> None: ...

    def run_once(
        self,
        *,
        symbol: str,
        period: str,
        interval: str,
        max_catchup_bars: int = 12,
    ) -> PaperCycleResult: ...
```

- [ ] **Step 1: Write RED tests for fresh-run, backlog, cap, and history-gap semantics**

Tests must cover these concrete cases using injected fake persistence/runtime/data loader:

```python
def test_fresh_runtime_processes_only_latest_eligible_bar(): ...
def test_existing_runtime_catches_up_oldest_first(): ...
def test_catchup_cap_leaves_remaining_backlog(): ...
def test_missing_last_processed_in_history_fails_closed(): ...
def test_no_new_bar_is_healthy_and_idempotent(): ...
def test_revision_conflict_reloads_and_continues_without_double_commit(): ...
```

For `test_existing_runtime_catches_up_oldest_first`, use a dataframe with at least 50 valid rows, set persisted `last_processed` to an older execution index, and assert the fake runtime receives execution indices in strictly ascending order.

For `test_missing_last_processed_in_history_fails_closed`, persisted state must be non-new with `last_processed="2020-01-01 00:00:00"` while the dataframe starts in 2025; assert `RuntimeError("persisted last_processed is outside loaded history")`.

- [ ] **Step 2: Run runner tests and verify RED**

```bash
pytest tests/test_paper_cycle.py -q
```

Expected: FAIL because `ai_trading.paper_cycle` does not exist.

- [ ] **Step 3: Implement eligibility discovery and bounded catch-up**

Implementation rules:

```python
runtime_key = build_runtime_key(symbol, interval)
persisted = persistence.load_runtime(runtime_key, starting_cash)
eligible = discover_eligible_execution_indices(df)

if persisted.is_new:
    targets = eligible[-1:]
else:
    # require durable last_processed to be present in/reconstructable from loaded history
    targets = eligible strictly newer than persisted.state.last_processed

targets = targets[:max_catchup_bars]
```

After each processed target, reload persistence before selecting/continuing subsequent work so a concurrent winning writer is visible. Treat a `processed=False` result caused by revision conflict or already-processed state as safe progress, then recompute remaining eligible work from durable state. Reject `max_catchup_bars < 1` with `ValueError`.

- [ ] **Step 4: Add PostgreSQL reconstruction/overlap integration test**

Using `TEST_DATABASE_URL`, create two separately constructed `PostgresPaperPersistence` and runner instances against one `runtime_key`. Process a sequence of multiple bars, reconstruct the runner, continue, then assert:

```python
assert final.revision == number_of_committed_bars
assert final.state.processed_bars == number_of_committed_bars
assert final.state.last_processed == expected_latest_timestamp
```

Also assert trade/audit/model/state rows do not partially advance when the existing transactional test hook forces a failure.

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
- Consumes: `PaperCycleRunner`, `build_paper_persistence()`, `HostedRuntimeStatus`, `HostedPaperSettings`.
- Produces: `ai-trading paper-cycle` command and `HostedPaperSettings.external_scheduler: bool`.

- [ ] **Step 1: Write RED test for external scheduler flag suppressing daemon startup**

```python
def test_external_scheduler_suppresses_daemon(monkeypatch) -> None:
    monkeypatch.setenv("AI_TRADING_HOSTED_PAPER", "1")
    monkeypatch.setenv("AI_TRADING_EXTERNAL_SCHEDULER", "1")
    settings = HostedPaperSettings.from_env()

    thread = start_hosted_paper_runtime(settings=settings, runner=lambda _: None)

    assert settings.external_scheduler is True
    assert thread is None
```

Keep the existing test proving daemon startup when hosted paper is enabled and external scheduling is false.

- [ ] **Step 2: Write RED CLI/status tests**

Use Typer's `CliRunner` and monkeypatch the persistence factory + `PaperCycleRunner`. Verify:

```text
ai-trading paper-cycle --symbol GC=F --period 5d --interval 5m --max-catchup-bars 12
```

builds the shared runtime key, writes `STARTING`, runs one bounded cycle, writes `RUNNING`, and exits 0. Inject a runner exception and assert exit non-zero with durable `ERROR`; inject status-write failure during exception handling and assert the original runner exception remains primary.

Status written for the scheduled executor must use `poll_seconds=300.0`, so stale threshold remains 900 seconds through existing status logic.

- [ ] **Step 3: Implement config and CLI**

Add:

```python
external_scheduler = os.getenv("AI_TRADING_EXTERNAL_SCHEDULER", "0").strip().lower() in {
    "1", "true", "yes", "on"
}
```

and include it in `HostedPaperSettings`.

`start_hosted_paper_runtime()` must return `None` when `external_scheduler` is true even if `enabled` is true, logging only a non-secret message such as `Hosted paper worker: external scheduler enabled`.

Add `@app.command("paper-cycle")` which:

1. builds persistence with `build_paper_persistence()`;
2. computes the runtime key through `build_runtime_key()`;
3. writes sanitized `STARTING` status;
4. calls `PaperCycleRunner.run_once(...)`;
5. reloads runtime state and writes `RUNNING` status including `last_processed`, processed count/equity/units, and a reason indicating processed/no-new-bar/backlog-pending;
6. on failure, best-effort writes sanitized `ERROR` then re-raises/returns non-zero.

Do not print a database URL or exception message that may contain one; printing exception class is allowed.

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

- [ ] **Step 1: Write RED workflow-structure test**

Parse `.github/workflows/paper-cycle.yml` as text or YAML and assert it contains all of:

```text
cron: "*/5 * * * *"
workflow_dispatch
concurrency
group: paper-cycle-production
cancel-in-progress: false
AI_TRADING_DATABASE_URL: ${{ secrets.AI_TRADING_DATABASE_URL }}
ai-trading paper-cycle --symbol GC=F --period 5d --interval 5m --max-catchup-bars 12
```

Also assert the file does not contain `postgresql://`, `postgres://`, or a literal `password=`.

- [ ] **Step 2: Run workflow test and verify RED**

```bash
pytest tests/test_paper_cycle_workflow.py -q
```

Expected: FAIL because workflow does not exist.

- [ ] **Step 3: Create production workflow**

Use this exact operational structure:

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

- [ ] **Step 4: Verify workflow tests + Ruff**

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
- Produces: dashboard fields for last processed execution bar and processed-bar count, without any provider/database metadata.

- [ ] **Step 1: Write RED dashboard test**

Build a fake persistence returning a state with:

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

Assert rendered HTML includes `Last processed`, that timestamp, `Processed bars`, and `17`. Assert it does not contain a fake database hostname supplied only through a raised storage exception.

- [ ] **Step 2: Run dashboard tests and verify RED**

```bash
pytest tests/test_dashboard.py tests/test_dashboard_runtime.py -q
```

Expected: FAIL because these state metrics are not rendered.

- [ ] **Step 3: Add state metrics without changing health semantics**

When storage is healthy, derive `last_processed` and `processed_bars` from the loaded `RuntimeState`; when unavailable, show `-`. Keep `/healthz` HTTP behavior and sanitized storage errors unchanged.

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
- Modify: issue `#19` operational notes after proof
- No schema redesign unless a failing compatibility test proves it necessary.

**Interfaces:**
- Consumes: connected Neon integration, Render environment mutation, GitHub Actions secret `AI_TRADING_DATABASE_URL`.
- Produces: production Neon database, Render dashboard-only mode, scheduled executor, recorded continuity evidence.

- [ ] **Step 1: Document production operating model**

README must state:

```text
Render: dashboard only when AI_TRADING_EXTERNAL_SCHEDULER=1
GitHub Actions: paper-cycle every 5 minutes
PostgreSQL: shared durable database selected by AI_TRADING_DATABASE_URL
Production runtime key: paper:GC=F:5m:online-river:v1
```

Document that a fresh runtime processes only the latest eligible bar, while established state catches up oldest-first up to 12 bars/run and fails closed if durable `last_processed` is outside loaded history.

- [ ] **Step 2: Run complete local/CI-equivalent verification before PR**

```bash
ruff check src tests
pytest -q
```

Expected: 0 Ruff errors and 0 test failures, including PostgreSQL integration under `TEST_DATABASE_URL` in CI.

- [ ] **Step 3: Open PR and require fresh CI GREEN**

Open the implementation PR from the feature branch to `main`. Do not merge until the PR run shows install, Ruff, and Pytest all successful with PostgreSQL 16 service healthy.

- [ ] **Step 4: Create Neon production project after code/CI approval**

Through the connected Neon integration:

- create project name `ai-trading-paper-production`;
- PostgreSQL version 16;
- use a European region when Neon exposes one compatible with the connected account;
- keep default branch as production;
- retrieve connection string only through `Neon.get_connection_string`;
- never place the returned value in chat or repository content.

Initialize application schema by starting the PostgreSQL backend against this URL through the deployed application path or an authorized database execution path. Verify tables exist: `paper_runtime_state`, `paper_model_state`, `paper_trades`, `paper_audit_events`, `paper_runtime_status`.

- [ ] **Step 5: Configure Render first in dashboard-only mode**

Set/merge these Render environment variables without replacing unrelated variables:

```text
AI_TRADING_DATABASE_URL=<Neon secret>
AI_TRADING_EXTERNAL_SCHEDULER=1
AI_TRADING_HOSTED_PAPER=1
AI_TRADING_HOSTED_SYMBOL=GC=F
AI_TRADING_HOSTED_PERIOD=5d
AI_TRADING_HOSTED_INTERVAL=5m
```

Allow the environment change to redeploy. Verify logs show dashboard start and `Hosted paper worker: external scheduler enabled`, with no daemon-thread start message. Verify `/healthz` reports storage reachable even before a fresh external heartbeat.

- [ ] **Step 6: Configure GitHub Actions secret or stop at the authorization boundary**

Required repository secret:

```text
AI_TRADING_DATABASE_URL=<same Neon secret>
```

If an authorized secret-write tool is available, set it without exposing the value. If not, record this as the single manual step required from the repository owner and do not paste the secret into chat, issue, PR, or source.

- [ ] **Step 7: Manually dispatch first paper cycle and capture baseline state**

After the secret exists, run `Paper Cycle` through `workflow_dispatch`. Require job success. Query Neon read-only and record non-secret continuity fields only:

```sql
SELECT runtime_key, revision, last_processed, processed_bars
FROM paper_runtime_state
WHERE runtime_key = 'paper:GC=F:5m:online-river:v1';

SELECT format, version, sha256
FROM paper_model_state
WHERE runtime_key = 'paper:GC=F:5m:online-river:v1';

SELECT engine_status, updated_at_utc
FROM paper_runtime_status
WHERE runtime_key = 'paper:GC=F:5m:online-river:v1';
```

- [ ] **Step 8: Prove restart/process continuity**

Trigger a Render redeploy without changing code, then manually dispatch another paper cycle after a newer eligible bar is available or run a controlled test cycle that is idempotent when no new bar exists. Query the same rows and prove:

- runtime key is unchanged;
- revision never decreases;
- `processed_bars` never decreases;
- model row remains present with valid checksum/version;
- status heartbeat is refreshed by executor, not Render daemon;
- dashboard reads the same durable values after Render process replacement.

- [ ] **Step 9: Observe scheduled path and finalize issue**

Observe at least one schedule-triggered `Paper Cycle` run after manual validation. Confirm no overlapping normal run due to workflow concurrency, and verify Neon durable status heartbeat updates. Update issue #19 with commit/PR/run identifiers and non-secret continuity evidence, then close it only if every acceptance criterion is met.

- [ ] **Step 10: Final production verification**

Require all of:

```text
main CI = success
latest Render deploy = live
Paper Cycle manual run = success
Paper Cycle scheduled run = success
Neon runtime row = present and advancing/idempotent
Neon model/status rows = present
Render daemon = suppressed
Dashboard /healthz = reachable
No live brokerage route = introduced
```

The temporary Render Free PostgreSQL instance remains untouched unless the user explicitly approves deletion.

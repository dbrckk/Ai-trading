# Continuous Paper Execution Design

Date: 2026-09-16
Status: written spec self-reviewed; pending user review
Scope: paper trading only
Tracking issue: #19

## Goal

Make the hosted paper-trading system continue executing on schedule even when the Render web service sleeps, while keeping one durable source of truth for runtime state, online model state, trades, audit events, and engine status.

The dashboard remains a read-only operational view. The paper executor becomes an independent one-shot scheduled process. No live broker routing is introduced.

## Current State

`main` already contains durable paper persistence from PR #18:

- `PaperPersistence` abstraction
- file and PostgreSQL backends
- revision-based optimistic concurrency control
- atomic state/model/trade/audit commits in PostgreSQL
- durable hosted runtime status
- dashboard reads through the persistence abstraction
- fail-closed behavior when PostgreSQL is configured but unavailable
- versioned/checksummed River model payloads

The production Render web service currently starts the dashboard and an in-process daemon worker. This worker works while the service is awake, but a free web service can sleep. Therefore the web process is not a reliable scheduler.

A temporary Render Free PostgreSQL instance exists, but it expires after 30 days. Neon is the selected long-lived PostgreSQL provider for this design.

## Chosen Architecture

### Runtime roles

There are two independent runtime roles:

1. **Dashboard service on Render**
   - serves HTML, `/api/status`, and `/healthz`
   - reads durable runtime/trade/status data from PostgreSQL
   - does not execute scheduled paper cycles when external scheduling is enabled

2. **One-shot paper executor in GitHub Actions**
   - runs from a scheduled workflow every 5 minutes
   - also supports `workflow_dispatch` for manual execution
   - loads market data
   - catches up eligible unprocessed bars chronologically
   - persists every processed bar through the existing transactional PostgreSQL backend
   - exits after the cycle instead of remaining resident

Both roles use the same database URL and the same stable runtime key.

### Database provider

Neon PostgreSQL is the durable production backend.

The existing `AI_TRADING_DATABASE_URL` contract remains unchanged. This avoids introducing provider-specific database code: Neon is consumed as ordinary PostgreSQL through `psycopg`.

The Render Free PostgreSQL database is not the long-term source of truth for this design.

## Stable Runtime Identity

The executor and dashboard must derive exactly the same runtime key:

```text
paper:{symbol}:{interval}:online-river:v1
```

For the current hosted configuration:

```text
paper:GC=F:5m:online-river:v1
```

Runtime-key construction must live in one shared helper. Neither CLI commands nor hosted/dashboard code may construct a production runtime key independently.

## One-Shot Cycle API

Introduce a focused application service, conceptually:

```python
class PaperCycleRunner:
    def run_once(
        self,
        *,
        symbol: str,
        period: str,
        interval: str,
        max_catchup_bars: int,
    ) -> PaperCycleResult: ...
```

The runner owns orchestration only. Trading decisions remain inside `PaperAutonomousRuntime` and risk controls remain inside `RiskEngine`.

A new CLI command exposes this service:

```text
ai-trading paper-cycle \
  --symbol GC=F \
  --period 5d \
  --interval 5m \
  --max-catchup-bars 12
```

The command must build persistence through `build_paper_persistence()`. If `AI_TRADING_DATABASE_URL` is configured and unusable, it fails closed.

## Catch-Up Semantics

### Why catch-up is required

Scheduled GitHub Actions executions can be delayed or skipped. A one-shot executor must therefore process missed closed bars on the next successful run instead of only looking at the newest bar.

### Chronological processing

For an existing persisted runtime:

1. Load the current persisted runtime state.
2. Determine all execution bars that are:
   - fully closed/eligible according to the existing signal/execution relationship,
   - newer than `state.last_processed`,
   - available in the downloaded history.
3. Process them oldest-first.
4. Persist each bar as its own atomic runtime commit.
5. Reload state/revision after a concurrency conflict before deciding whether more catch-up work remains.

Sequential processing is required because the River model learns online and each bar changes the state used by the next bar.

### History-gap protection

An existing runtime must never jump from an old durable `last_processed` value directly to the newest available history merely because the requested market-data window no longer contains the missing bars.

If the runtime has durable history but the loader cannot establish a continuous eligible sequence after `last_processed`, the cycle must fail with an explicit history-gap error. It must not advance state, model, audit, or trades beyond the unknown gap.

Recovery then requires a wider supported history window or an explicit operator decision; silent loss of scheduled bars is not allowed.

### Fresh runtime initialization

A completely new runtime must **not replay the whole downloaded history**.

If no prior state exists, the first production cycle processes only the latest eligible execution bar. Historical rows are used for feature construction, not as a backlog.

After that first commit, normal catch-up semantics apply.

### Catch-up cap

`max_catchup_bars` prevents an unexpectedly large backlog from making one scheduled job unbounded.

Default production value: `12` bars (one hour at 5-minute intervals).

If more eligible bars remain after the cap:

- commit the first `max_catchup_bars` oldest bars,
- report that catch-up remains pending,
- allow the next scheduled run to continue from durable state.

The cap is operational, not a trading shortcut: skipped backlog remains durable through `last_processed` and is not silently discarded.

## Runtime Step Refactor

The current `PaperAutonomousRuntime.step(df)` chooses the latest eligible execution bar. Catch-up requires deterministic processing of a specific execution bar.

Refactor without changing trading logic:

```python
step(df)
```

remains as the compatibility/latest-bar entry point, while an internal or explicit method accepts a specific eligible execution index, for example:

```python
step_at(df, execution_idx)
```

Both paths must share the same implementation for:

- feature generation
- online learning
- prediction
- risk evaluation
- paper broker rebalance
- trade snapshot creation
- state/model/audit commit

No duplicated trading logic is allowed between latest-only and catch-up paths.

## Scheduler Workflow

Add a dedicated workflow such as:

```text
.github/workflows/paper-cycle.yml
```

Triggers:

```yaml
on:
  schedule:
    - cron: "*/5 * * * *"
  workflow_dispatch:
```

Required properties:

- minimal `contents: read` permissions
- Python 3.11
- dependency caching
- `AI_TRADING_DATABASE_URL` from a GitHub Actions secret
- hosted symbol/period/interval passed explicitly
- `timeout-minutes` large enough for dependency install + bounded catch-up
- a workflow-level concurrency group, e.g. `paper-cycle-production`
- `cancel-in-progress: false`

The existing database revision check remains the final correctness guard if two executors overlap despite workflow serialization.

No database URL may appear in workflow logs or committed YAML.

## Hosted Worker Mode

The Render dashboard must not run the resident paper daemon when external scheduling is active.

Introduce an explicit configuration flag, for example:

```text
AI_TRADING_EXTERNAL_SCHEDULER=1
```

Behavior:

- absent/false: preserve current embedded worker behavior for local/backward-compatible use
- true: serve dashboard only; do not start the daemon thread

This makes the operating mode explicit instead of inferring it from the presence of a database URL.

Production Render configuration will set the flag true **before Neon becomes the production source of truth**, so the legacy resident worker cannot initialize or mutate the new production runtime row.

## Durable Engine Status

The scheduled one-shot executor writes status through the existing persistence interface.

Suggested lifecycle per invocation:

1. `STARTING` before market-data work
2. `RUNNING` after each successful processed/caught-up bar, with fresh heartbeat timestamp
3. `RUNNING` with a no-new-bar reason when the invocation is healthy but nothing is eligible
4. `ERROR` on genuine executor failure when status persistence itself is available

If writing `ERROR` fails because storage is unavailable, the original exception must remain the primary failure.

The dashboard continues computing stale status from durable heartbeat age. Therefore dashboard process uptime is independent from engine freshness.

## Paper-Only Safety

This design does not add any live broker adapter, credential path, order-routing API, or bypass around the existing risk engine.

Acceptance requires:

- paper broker remains the only execution path
- no live brokerage dependency or environment variable is introduced
- risk evaluation remains mandatory before paper rebalance
- storage failure remains fail-closed

## Secrets and Provider Configuration

### Neon

Create one Neon project for the paper runtime after this written spec is approved.

Use the default production branch/database unless a compelling operational reason emerges during implementation.

Retrieve the privileged PostgreSQL connection string only through the connected Neon integration. Never write it to repository files, issue bodies, PR comments, logs, test fixtures, or user-visible output.

### Render

Set:

```text
AI_TRADING_DATABASE_URL=<Neon PostgreSQL secret>
AI_TRADING_EXTERNAL_SCHEDULER=1
```

using Render environment variables.

### GitHub Actions

Set repository secret:

```text
AI_TRADING_DATABASE_URL=<same Neon PostgreSQL secret>
```

The current GitHub connector does not expose repository secret mutation. If no authorized secret-write integration becomes available during rollout, secret insertion is the single manual control-plane step required from the repository owner. The secret value itself must never be pasted into chat or committed.

## Failure and Concurrency Behavior

### Database unavailable

- executor exits non-zero
- no fallback to file persistence
- dashboard reports storage unavailable
- no fresh account is synthesized

### Market-data failure

- executor exits non-zero after best-effort durable ERROR status
- no state/model/trade commit occurs for an incomplete bar

### History gap

- executor exits non-zero
- durable `last_processed` is not advanced across the gap
- the dashboard reports stale/error status through the durable status channel when possible

### Revision conflict

- treat as a safe concurrent loser, not data corruption
- discard the locally computed losing state/model
- reload durable state
- continue only if another eligible bar remains within the invocation catch-up budget

### Duplicate scheduler invocation

Workflow concurrency reduces overlap, while runtime revision CAS and trade event idempotence provide correctness if overlap still occurs.

## Testing Strategy

All implementation follows TDD.

### Unit tests

- shared runtime-key builder returns identical key for dashboard/executor
- fresh cycle processes only latest eligible bar
- existing runtime returns missed bars oldest-first
- history gap fails closed instead of jumping to newest data
- catch-up cap is enforced without discarding remaining backlog
- latest-only `step()` and targeted step share trading behavior
- no-new-bar cycle is healthy and idempotent
- external-scheduler flag suppresses hosted daemon startup
- configured database failure remains fail-closed
- worker failure is not masked by status-write failure

### PostgreSQL integration tests

Using the existing PostgreSQL 16 GitHub Actions service:

- multiple catch-up bars survive reconstruction of persistence/runtime objects
- model/state revisions advance once per processed bar
- duplicate/overlap invocation commits each logical bar at most once
- transaction rollback leaves no partial trade/audit/model/state mutation
- dashboard can read state/status written by a separately constructed cycle runner

### Workflow validation

Tests or static assertions should verify the workflow includes:

- 5-minute cron
- `workflow_dispatch`
- concurrency protection
- secret reference rather than literal database URL
- paper-cycle command with explicit hosted parameters

## Rollout Sequence

After implementation and CI are green:

1. Create the Neon production project and retrieve its connection string through the authorized integration.
2. Initialize/verify the schema using the application PostgreSQL backend without processing a market bar.
3. Set `AI_TRADING_EXTERNAL_SCHEDULER=1` on Render first, so the next Render process is dashboard-only.
4. Set the Neon URL as `AI_TRADING_DATABASE_URL` on Render and redeploy.
5. Verify Render starts the dashboard without the resident daemon and reads the empty/new Neon runtime state safely.
6. Configure the same Neon URL as the GitHub Actions `AI_TRADING_DATABASE_URL` repository secret.
7. Manually run `paper-cycle` once with `workflow_dispatch`; this executor owns initialization of the production paper runtime.
8. Verify Neon tables contain runtime state, model, status, audit and any trade rows produced.
9. Record state fields needed for continuity proof: `runtime_key`, `revision`, `last_processed`, `processed_bars`, model checksum, latest status timestamp.
10. Redeploy/restart the Render dashboard and verify it reads the same persisted runtime without mutation or reset.
11. Trigger a second one-shot cycle.
12. Verify the same runtime row advances from the prior revision rather than resetting.
13. Verify dashboard `/api/status` and `/healthz` reflect the externally updated durable status.
14. Observe at least one scheduled invocation path after manual validation.
15. Retire the temporary Render Free PostgreSQL instance only after continuity is proven and only with explicit user approval, because deletion is destructive.

## Observability

The dashboard should make the operating model clear enough to diagnose failures without opening logs.

At minimum it should expose existing fields plus:

- engine status
- last heartbeat
- heartbeat age
- stale reason
- last processed execution bar when runtime state is available
- processed-bar count when runtime state is available

Do not expose provider hostname, database name, username, password, or connection URL.

## Out of Scope

- live broker execution
- live brokerage credentials
- paid Render upgrades
- redesigning the strategy/model/risk engine
- multiasset production scheduling
- automatic deletion of the existing Render Free PostgreSQL instance
- changing the persistence schema merely because Neon is the provider
- sub-5-minute execution cadence

## Acceptance Criteria

The work is complete only when all of the following are demonstrated:

1. Production paper execution does not depend on Render web-service uptime.
2. A one-shot scheduled command processes eligible 5-minute bars idempotently.
3. Delayed executions catch up missed bars chronologically and with a bounded per-run cap.
4. A fresh runtime processes only the latest eligible bar instead of replaying history.
5. A missing history segment fails closed instead of silently skipping bars.
6. GitHub Actions schedules the one-shot executor every 5 minutes and prevents normal overlapping runs.
7. PostgreSQL revision CAS still prevents double commits under forced overlap.
8. Neon is the shared durable source of truth for executor and dashboard.
9. Render runs dashboard-only when external scheduling is enabled.
10. State, model, trades, audit history, and heartbeat survive Render redeploys and separate executor processes.
11. Dashboard freshness reflects the external executor heartbeat rather than dashboard process uptime.
12. PostgreSQL, market-data, or history-gap failures fail closed and never reset/advance the paper account silently.
13. All CI tests, including PostgreSQL integration and workflow checks, pass.
14. A production continuity proof records the same runtime key advancing across at least one executor restart/redeploy boundary.
15. Live trading remains disabled.

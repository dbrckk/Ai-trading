# Cloudflare Paper Scheduler Design

Date: 2026-09-16
Repository: `dbrckk/Ai-trading`
Status: proposed implementation design

## Context

The production paper-trading runtime is already durable and paper-only:

- Render hosts the dashboard/web service.
- Neon PostgreSQL stores runtime state, River model state, audit events, trades, and runtime status.
- `PaperCycleRunner` performs one-shot execution with chronological catch-up, a bounded backlog, and PostgreSQL revision CAS protection.
- Render runs with `AI_TRADING_EXTERNAL_SCHEDULER=1`, so its embedded daemon is disabled.
- GitHub Actions `workflow_dispatch` has successfully executed a real production paper cycle against Neon.
- The same durable state survived a Render redeploy.

The remaining production gap is scheduling. GitHub Actions `schedule` has not emitted any scheduled runs despite multiple valid cron forms and repeated observations after deployment. The command, secret, persistence layer, and manual workflow execution are known-good; the failure is isolated to periodic invocation.

Alternative schedulers were investigated:

- Render Cron is operationally suitable but has a paid minimum.
- Vercel Hobby cron does not provide the required five-minute cadence.
- Neon Function Triggers are not available for this project.
- Neon `pg_cron` is available, but the database does not expose an outbound HTTP extension that could wake the Render execution endpoint.

The selected architecture is therefore Cloudflare Workers Cron as the external free scheduler, with Render remaining the execution host and Neon remaining the durable source of truth.

## Goals

1. Execute the production paper cycle approximately every five minutes without relying on the sleeping Render process to self-schedule.
2. Keep the system strictly paper-only.
3. Preserve the existing durable runtime key and all existing catch-up/idempotence semantics.
4. Wake the Render Free web service through an authenticated HTTP request when necessary.
5. Keep all scheduler credentials out of Git, logs, dashboard payloads, and error messages.
6. Retain GitHub Actions `workflow_dispatch` as an operator fallback.
7. Keep the dashboard able to report a stale executor when scheduled calls stop arriving.
8. Require as little manual Cloudflare configuration as possible and document the exact one-time steps.

## Non-goals

- Live brokerage or real-money order routing.
- User-selectable symbols, intervals, strategies, or risk settings through the scheduler endpoint.
- Moving the trading engine into JavaScript or Cloudflare Workers.
- Replacing Neon persistence.
- Replacing the Render dashboard.
- Building a general-purpose authenticated job API.
- Guaranteeing execution at an exact wall-clock second. Catch-up remains the mechanism for delayed invocations.

## Chosen architecture

```text
Cloudflare Cron Trigger (every 5 minutes)
            |
            v
Cloudflare Worker scheduled() handler
            |
            | HTTPS POST + Bearer token
            v
Render: POST /internal/paper-cycle
            |
            v
Existing PaperCycleRunner
            |
            v
Neon PostgreSQL durable runtime
            |
            v
Render dashboard reads the same state
```

Cloudflare is only a trigger. It does not contain trading logic, model state, market-history logic, or database credentials.

Render remains the only service that imports and runs the Python trading package. Neon remains the only durable runtime store.

## Runtime identity and production settings

The production runtime identity remains exactly:

```text
paper:GC=F:5m:online-river:v1
```

The scheduler request must not be able to override production trading parameters.

The Render endpoint resolves settings server-side from the same production configuration used by the existing one-shot runner. Initial production values remain:

- symbol: `GC=F`
- interval: `5m`
- period: `5d`
- max catch-up bars: `12`
- status freshness / poll cadence: `300` seconds

If these settings later change, they change through deployment/environment configuration, not through the incoming HTTP body or query string.

## Render scheduler endpoint

### Route

```text
POST /internal/paper-cycle
```

The endpoint is intentionally not part of the public dashboard API surface.

### Authentication

Render receives a new environment variable:

```text
AI_TRADING_SCHEDULER_TOKEN
```

Cloudflare receives the same value as a Worker secret named:

```text
SCHEDULER_TOKEN
```

The Worker sends:

```text
Authorization: Bearer <token>
```

The Render handler:

1. Requires the `Authorization` header.
2. Requires the `Bearer ` scheme.
3. Compares the supplied token with `AI_TRADING_SCHEDULER_TOKEN` using a timing-safe comparison.
4. Returns `401` for missing or invalid credentials.
5. Never includes either token, the database URL, database host, or exception text in its response.

If `AI_TRADING_SCHEDULER_TOKEN` is absent from Render, the endpoint fails closed with a generic `503` rather than accepting unauthenticated calls.

### Request contract

The production request has no required body and no user-controlled trading parameters.

Any query parameter or JSON body is ignored for runtime configuration. The endpoint always uses server-side production settings.

### Response contract

Successful response:

```json
{
  "ok": true,
  "processed": 0,
  "status": "RUNNING"
}
```

`processed` is the number of execution bars committed during that invocation. It may be zero when there is no unseen eligible execution bar or when another authorized executor has already advanced the same durable revision.

The response must remain deliberately small and must not expose model data, database metadata, secret values, raw provider errors, or detailed trade internals.

Expected status codes:

- `200`: request authenticated and cycle completed, safely no-op'd, or lost a benign persistence race to an executor that already advanced the same runtime.
- `401`: invalid/missing scheduler token.
- `503`: scheduler endpoint unavailable because required configuration/storage initialization failed.
- `500`: sanitized unexpected execution failure.

A benign revision conflict is not exposed as an HTTP failure because logical progress has already occurred elsewhere. It returns `200` with no duplicate commit.

Every actual execution failure must still update durable runtime status to `ERROR` on a best-effort basis, following the same error-sanitization rules as the CLI.

## Shared execution service

HTTP and CLI must not grow separate paper-cycle implementations.

The existing one-shot orchestration is extracted or reused behind one shared callable service, conceptually:

```python
run_production_paper_cycle(...)
```

Both entry points call the same service:

```text
ai-trading paper-cycle  ---> shared service <--- POST /internal/paper-cycle
```

The shared service owns:

- persistence construction;
- runtime-key construction;
- market-history loading;
- `PaperCycleRunner` invocation;
- STARTING/RUNNING/ERROR durable status transitions;
- sanitized error boundaries;
- result summary.

This prevents divergence between manual GitHub fallback and Cloudflare-triggered production execution.

## Idempotence and concurrency

Cloudflare delivery is treated as at-least-once, not exactly-once.

No correctness property depends on a scheduler firing exactly once.

Existing protections remain authoritative:

1. `PaperCycleRunner` identifies unseen eligible bars chronologically.
2. The persisted `last_processed` prevents already-committed execution bars from being replayed.
3. PostgreSQL revision CAS is the final concurrency guard.
4. If two scheduler calls race, only one may commit a particular revision.
5. A loser returns a safe no-op result and must not create a duplicate trade or model update.

The Cloudflare Worker does not implement distributed locking.

## Catch-up behavior

Scheduled invocations can be delayed by platform wake-up time or transient network failures.

The existing bounded catch-up remains unchanged:

- unseen eligible bars are processed oldest-first;
- at most 12 execution bars are attempted in one invocation;
- the dataframe is truncated appropriately for each historical execution point, preserving no-lookahead behavior;
- if `last_processed` is older than the available history window, execution fails closed rather than silently skipping bars;
- runtime state is reloaded after each attempt/conflict.

This means scheduler timing affects latency, not logical correctness, as long as the historical gap remains recoverable inside the configured provider window.

## Cloudflare Worker

A minimal Worker is stored in the repository under:

```text
infra/cloudflare-paper-scheduler/
```

Expected files:

```text
infra/cloudflare-paper-scheduler/src/index.js
infra/cloudflare-paper-scheduler/wrangler.toml
infra/cloudflare-paper-scheduler/README.md
```

No secret value is committed.

The Worker has two environment inputs:

- `TARGET_URL`: non-secret Render endpoint URL, ending in `/internal/paper-cycle`.
- `SCHEDULER_TOKEN`: Cloudflare secret, never stored in `wrangler.toml`.

Conceptual Worker behavior:

```javascript
export default {
  async scheduled(event, env, ctx) {
    ctx.waitUntil(
      fetch(env.TARGET_URL, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${env.SCHEDULER_TOKEN}`,
          "User-Agent": "ai-trading-cloudflare-scheduler/1",
        },
      }).then(async (response) => {
        if (!response.ok) {
          throw new Error(`paper cycle failed with HTTP ${response.status}`);
        }
      }),
    );
  },
};
```

The Worker must never log the token or response body on error. HTTP status is sufficient for operator diagnostics because detailed execution state is already persisted in Neon and surfaced by the dashboard.

## Cloudflare cron

Production cron:

```text
*/5 * * * *
```

Cloudflare Cron Triggers use UTC. No timezone conversion is needed because execution is every five minutes continuously.

A single production trigger is configured.

## GitHub Actions after cutover

`.github/workflows/paper-cycle.yml` remains in the repository but loses its `schedule:` block.

It retains:

```yaml
workflow_dispatch:
```

This gives an operator an independent manual fallback that has already been proven to connect to Neon successfully.

The GitHub workflow keeps the `AI_TRADING_DATABASE_URL` secret and the durable-database preflight. It must not become a second automatic scheduler after Cloudflare is enabled.

## Render deployment mode

Render continues to use:

```text
AI_TRADING_EXTERNAL_SCHEDULER=1
```

The embedded hosted daemon remains disabled.

New environment variable:

```text
AI_TRADING_SCHEDULER_TOKEN=<secret>
```

`AI_TRADING_DATABASE_URL` remains unchanged and continues to point at Neon.

A Cloudflare invocation is also the wake-up request for the Render Free web service when Render has scaled down due to inactivity.

## Dashboard and health semantics

The dashboard continues to read runtime status from Neon.

The existing freshness rule remains:

```text
STALE after 3 x 300 seconds = 15 minutes without a fresh runtime heartbeat
```

No Cloudflare-specific health state is required. The durable execution heartbeat is more useful than merely knowing the Worker fired.

Expected behavior:

- recent successful cycle -> `RUNNING` / healthy executor;
- scheduler stops or endpoint repeatedly fails -> `STALE` after 15 minutes;
- cycle raises an execution/storage error -> `ERROR`;
- Render web server itself can remain healthy while executor state is `STALE` or `ERROR`.

## Security model

### Secrets

Three independent secret locations exist after cutover:

- Render: `AI_TRADING_DATABASE_URL`
- Render: `AI_TRADING_SCHEDULER_TOKEN`
- Cloudflare Worker: `SCHEDULER_TOKEN`

GitHub keeps `AI_TRADING_DATABASE_URL` only for manual fallback execution.

The scheduler token must not be reused as a database password, GitHub token, Cloudflare API token, or any unrelated credential.

### Token generation

Use at least 32 random bytes encoded as URL-safe text. The token is generated once during rollout and copied to Render and Cloudflare only.

### Endpoint attack surface

The endpoint cannot:

- select a symbol;
- select an interval;
- modify risk settings;
- enable live trading;
- provide database configuration;
- submit order instructions.

Its only authorized action is: run one bounded iteration of the already-configured paper executor.

### Logging

Never log:

- Authorization headers;
- scheduler token values;
- Neon connection strings;
- raw database exceptions that can contain connection information.

Render and Cloudflare logs may contain only sanitized status/error type information.

## Failure handling

### Cloudflare cannot reach Render

The Worker invocation fails. No state is advanced. A future cron invocation retries naturally; bounded catch-up handles recoverable missed bars.

### Render wakes slowly

The HTTP request waits for the service to wake. If the invocation ultimately fails, the next trigger retries. No correctness state exists in Cloudflare.

### Invalid token

Render returns `401`. No persistence or market-data operation starts.

### Neon unavailable

The endpoint fails closed. The application does not fall back to file persistence because `AI_TRADING_DATABASE_URL` is configured for production. Durable status update is best-effort only if persistence itself is unavailable.

### Market-data provider unavailable

The endpoint returns a sanitized failure. Runtime state is not advanced for data that was not safely processed. The next scheduled invocation can retry/catch up.

### Concurrent Cloudflare and manual GitHub invocation

PostgreSQL revision CAS resolves the race. If one executor commits first, the other returns a successful safe no-op. No duplicate logical commit is permitted.

## Testing strategy

Implementation follows TDD.

### Authentication tests

- request without Authorization -> `401`;
- wrong scheme -> `401`;
- wrong token -> `401`;
- missing server token configuration -> `503`;
- valid token -> execution service called exactly once;
- request body cannot override symbol/interval/risk settings;
- secret/token/database URL never appears in public response.

### Execution integration tests

- HTTP path and CLI call the same shared production-cycle service;
- successful no-op returns `200` and `processed=0`;
- successful catch-up returns committed count;
- persistence conflict returns a successful safe no-op without duplicate commit;
- internal exception becomes sanitized public error and durable `ERROR` status when possible.

### Cloudflare Worker tests

- scheduled handler sends POST to configured target;
- sends Bearer token from secret binding;
- does not send trading configuration in request body/query;
- non-2xx response rejects the scheduled task;
- logs/errors never contain token value or response body.

### Workflow tests

The existing structural workflow test changes to assert:

- `workflow_dispatch` still exists;
- no `schedule:` block exists;
- durable DB secret guard remains;
- production manual command remains unchanged.

### Full regression verification

Before merge:

- Ruff green;
- full Pytest green;
- PostgreSQL 16 persistence tests green;
- Worker tests green;
- no secret-like values committed.

## Rollout sequence

The rollout is intentionally ordered so there is never a period with two uncontrolled automatic schedulers.

1. Merge and deploy the authenticated Render endpoint while GitHub `schedule` still exists.
2. Generate `AI_TRADING_SCHEDULER_TOKEN` securely.
3. Add the token to Render and redeploy.
4. Verify unauthorized endpoint calls are rejected.
5. Verify one authorized endpoint invocation manually and confirm Neon advances/no-ops correctly.
6. Deploy the Cloudflare Worker with `TARGET_URL` and secret `SCHEDULER_TOKEN`.
7. Add the `*/5 * * * *` Cloudflare Cron Trigger.
8. Observe at least one real Cloudflare scheduled invocation reach Render and update the Neon heartbeat.
9. Remove the GitHub Actions `schedule:` trigger, leaving `workflow_dispatch` only.
10. Verify another Cloudflare scheduled invocation after GitHub scheduling is disabled.
11. Verify dashboard status remains fresh and Render logs still show embedded scheduler disabled.
12. Update and close GitHub issue #19 only after this production proof is complete.

If Cloudflare deployment cannot be completed, do not remove GitHub `workflow_dispatch` and do not claim scheduling is stable.

## Manual Cloudflare boundary

The current ChatGPT environment has no Cloudflare connector. Repository changes, Render changes, Neon checks, tests, and GitHub changes can be automated here, but Cloudflare account deployment requires a one-time user action.

When implementation reaches that boundary, the user will receive exact instructions for:

1. creating/importing the Worker from the repository source;
2. setting `TARGET_URL`;
3. creating the secret `SCHEDULER_TOKEN`;
4. creating the five-minute Cron Trigger;
5. confirming the deployment.

No database credential is needed in Cloudflare.

## Rollback

Rollback is simple because Cloudflare holds no durable state.

If Cloudflare scheduling fails after cutover:

1. disable/delete the Cloudflare Cron Trigger;
2. keep Render in `AI_TRADING_EXTERNAL_SCHEDULER=1`;
3. use GitHub `workflow_dispatch` manually while diagnosing;
4. optionally restore a GitHub `schedule` in a reviewed code change if GitHub scheduling becomes reliable again.

Neon runtime/model/trade/audit data requires no rollback.

## Acceptance criteria

The architecture is production-complete only when all of the following are observed:

1. Unauthorized `/internal/paper-cycle` requests are rejected.
2. An authorized request executes the existing paper-cycle path without accepting request-controlled trading settings.
3. The endpoint and Worker leak no scheduler/database secret.
4. Cloudflare executes a real scheduled invocation.
5. Neon heartbeat/state confirms that invocation reached the durable runtime.
6. A delayed invocation catches up chronologically without duplicate processing.
7. Render remains dashboard-only with the embedded daemon disabled.
8. GitHub Actions retains manual `workflow_dispatch` fallback but no automatic schedule.
9. Dashboard reports `STALE` when no executor heartbeat is written for 15 minutes.
10. Full repository CI and Worker tests are green.
11. Live brokerage remains disabled and out of scope.
12. GitHub issue #19 contains the final production evidence and is closed only after these checks pass.

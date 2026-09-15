# Durable paper-trading persistence design

Date: 2026-09-15
Status: proposed, user-approved in chat pending written-spec review
Scope: paper trading only

## Goal

Make the hosted paper runtime survive Render restarts, redeploys, and ephemeral filesystem loss without resetting cash, positions, processed-bar state, trade history, audit history, or the online River model.

The change must not enable live broker routing or weaken the existing risk engine.

## Current problem

The hosted service currently persists runtime data only under local `artifacts/` files:

- `runtime_state.json`
- `trades.jsonl`
- `audit.jsonl`
- `models/online-river.joblib`
- `runtime_status.json`

On the current Render Free web service, local filesystem state is not a durable source of truth. A restart can therefore reset the paper account, lose trades, lose learned-model state, and allow an already-processed market bar to be processed again.

## Chosen architecture

Introduce one persistence facade used by the paper runtime and dashboard. The facade selects a backend from configuration:

- `PostgresPaperPersistence` when `AI_TRADING_DATABASE_URL` is present.
- `FilePaperPersistence` when no database URL is configured.

The file backend preserves local-development and existing-test behavior. The Postgres backend becomes the production source of truth.

The public behavior of `PaperAutonomousRuntime` remains paper-only. Existing risk checks, scheduler semantics, and trading decisions stay unchanged.

## Runtime identity

Persistent state must be isolated by a stable `runtime_key` so changing symbol or timeframe cannot accidentally reuse incompatible state.

Hosted runtime key format:

`paper:{symbol}:{interval}:online-river:v1`

Examples:

- `paper:GC=F:5m:online-river:v1`
- `paper:SI=F:15m:online-river:v1`

The hosted runtime constructs the key from its configured symbol and interval and injects it into the persistence facade.

## Persistence contract

The runtime should use a higher-level persistence interface instead of independently writing state, trades, audit records, and model files.

Conceptual interface:

```python
class PaperPersistence(Protocol):
    def load_runtime(self, runtime_key: str, starting_cash: float) -> PersistedRuntime: ...
    def commit_step(self, runtime_key: str, commit: RuntimeStepCommit) -> None: ...
    def list_trades(self, runtime_key: str | None = None, *, limit: int | None = None) -> tuple[TradeSnapshot, ...]: ...
    def append_runtime_status(self, runtime_key: str, status: HostedRuntimeStatus) -> None: ...
    def load_runtime_status(self, runtime_key: str) -> HostedRuntimeStatus | None: ...
```

`PersistedRuntime` contains:

- `RuntimeState`
- serialized online-model payload, if present

`RuntimeStepCommit` contains all state that belongs to one processed bar:

- new `RuntimeState`
- serialized online-model payload
- optional `TradeSnapshot`
- audit event payload

The Postgres backend commits these values in one transaction.

## Transactional safety

A processed bar must be committed atomically.

For Postgres, one successful transaction must include:

1. insert the trade event if the bar generated a trade;
2. insert the audit event;
3. upsert the new runtime state;
4. upsert the serialized online model;
5. commit.

If any part fails, the whole transaction rolls back.

This prevents partial states such as:

- trade recorded but `last_processed` still old;
- model learned twice after restart;
- state advanced but audit record missing.

The runtime must raise on persistence failure. It must not silently fall back from Postgres to local files when `AI_TRADING_DATABASE_URL` is configured.

## Database schema

### `paper_runtime_state`

One row per `runtime_key`.

Fields:

- `runtime_key text primary key`
- `cash double precision not null`
- `units double precision not null`
- `last_price double precision not null`
- `peak_equity double precision not null`
- `day_start_equity double precision not null`
- `last_processed text null`
- `processed_bars bigint not null`
- `last_learning_cycle_bar bigint not null`
- `updated_at timestamptz not null default now()`

### `paper_model_state`

One current online-model snapshot per runtime.

Fields:

- `runtime_key text primary key references paper_runtime_state(runtime_key) on delete cascade`
- `format text not null`
- `version integer not null`
- `payload bytea not null`
- `sha256 text not null`
- `updated_at timestamptz not null default now()`

The initial format is `joblib-river-v1`.

Model payloads are stored in Postgres rather than local disk or object storage so model + state can participate in the same database transaction.

### `paper_trades`

Append-only trade history.

Fields:

- `id bigserial primary key`
- `runtime_key text not null`
- `event_key text not null`
- `timestamp_utc text not null`
- `symbol text not null`
- `side text not null`
- `quantity double precision not null`
- `price double precision not null`
- `status text not null`
- `pnl double precision not null default 0`
- `confidence double precision null`
- `strategy text not null`
- `created_at timestamptz not null default now()`
- unique `(runtime_key, event_key)`

`event_key` is a deterministic SHA-256 generated from immutable trade fields. It protects against duplicate inserts if the same logical event is retried.

### `paper_audit_events`

Append-only hash-chained audit history per runtime.

Fields:

- `id bigserial primary key`
- `runtime_key text not null`
- `timestamp_utc timestamptz not null`
- `event text not null`
- `payload jsonb not null`
- `prev_hash text not null`
- `hash text not null`
- unique `(runtime_key, hash)`

The previous hash is selected and the new audit row inserted inside the same transaction as the runtime-step commit.

### `paper_runtime_status`

Current hosted-worker status, used by the dashboard and health API after restarts.

Fields:

- `runtime_key text primary key`
- `engine_status text not null`
- `symbol text not null`
- `interval text not null`
- `updated_at_utc timestamptz not null`
- `payload jsonb not null`

The payload stores the remaining `HostedRuntimeStatus` fields for forward compatibility.

## Dashboard behavior

When Postgres persistence is configured, the dashboard reads trades and runtime status from Postgres instead of local artifacts.

The existing HTML view, `/api/status`, and `/healthz` remain read-only.

The dashboard must not synthesize a fresh paper account if Postgres is configured but unavailable. A persistence-read failure should be surfaced as an unavailable/error state rather than showing misleading zeroed values.

## Configuration

New environment variable:

- `AI_TRADING_DATABASE_URL`

Recommended production value: a PostgreSQL connection string from the Supabase session pooler with TLS enabled.

Rules:

- secrets never enter Git, logs, status payloads, or dashboard HTML;
- no database URL means file backend;
- database URL present but invalid/unreachable means fail closed;
- no automatic fallback to files after a Postgres error.

## Schema initialization

Add an idempotent schema initializer using `CREATE TABLE IF NOT EXISTS` and required indexes/constraints.

The production process calls schema initialization once during startup before the hosted worker begins processing bars.

Startup must stop the worker if schema initialization fails.

No destructive migrations are part of this change.

## Existing local artifacts

There will be no silent automatic import of old local artifacts into Postgres.

On first production use with an empty database, the Postgres backend initializes a fresh paper runtime at configured starting cash.

Reason: automatic merging of ephemeral files with a new durable source of truth creates ambiguity about which state is authoritative and can duplicate trades or model-learning history.

A separate explicit import command can be designed later if preserving legacy paper artifacts becomes necessary.

## Model serialization

The runtime keeps the existing River model behavior but serializes/deserializes through an in-memory byte payload for persistent backends.

Requirements:

- deterministic checksum using SHA-256;
- verify checksum before deserializing;
- reject unknown format/version;
- never silently replace a corrupt persisted model with a blank model when runtime state already exists;
- a brand-new runtime with no state/model may create a fresh `RiverDirectionModel`.

## File backend behavior

`FilePaperPersistence` adapts the current JSON/JSONL/joblib storage so local workflows and most unit tests remain fast.

It should preserve current paths by default and maintain backward compatibility with existing artifact files.

The file backend is not claimed to provide cross-file transactional durability. Production durability guarantees apply to the Postgres backend.

## Error handling

The hosted worker must enter `ERROR` status and stop processing when:

- schema initialization fails;
- durable state cannot be read;
- a model checksum is invalid;
- a Postgres transaction fails;
- persisted state is structurally invalid.

The system must not reset cash, units, `last_processed`, processed-bar counters, or model state as a recovery shortcut.

## Testing strategy

Development follows TDD.

### Unit tests

Cover:

- backend selection from environment;
- runtime-key construction;
- fresh-runtime initialization;
- model serialization/checksum validation;
- file-backend compatibility;
- fail-closed behavior when Postgres is configured but unavailable;
- dashboard reading through the persistence facade.

### Postgres integration tests

GitHub Actions should run a temporary PostgreSQL service and verify:

- schema creation is idempotent;
- state survives a new persistence-object/process instance;
- trade listing survives restart;
- model bytes survive restart and checksum validation;
- one `commit_step` writes state + model + trade + audit atomically;
- forced failure inside a transaction leaves none of those changes committed;
- duplicate logical trade retries do not create a second trade row;
- runtime status survives a new process instance.

No CI test depends on Supabase credentials.

## Rollout sequence

1. Add persistence protocols/data structures and keep file behavior green.
2. Add Postgres schema and backend.
3. Move runtime state/model/trade/audit writes behind `commit_step`.
4. Move hosted status and dashboard reads behind persistence.
5. Add Postgres integration coverage in CI.
6. Configure `AI_TRADING_DATABASE_URL` on Render.
7. Deploy while remaining paper-only.
8. Verify a paper state, restart/redeploy the service, and confirm the same state/trades/model are recovered.

## Out of scope

This design does not include:

- live brokerage or real-money order routing;
- paid Render disk migration;
- solving Render Free idle sleep;
- multi-user authentication;
- a manual legacy-artifact import tool;
- portfolio-schema redesign beyond what is necessary for the current hosted runtime.

## Acceptance criteria

The change is complete when all of the following are true:

1. With `AI_TRADING_DATABASE_URL` configured, Postgres is the only source of truth for paper runtime state, online model, trades, audit history, and hosted status.
2. Restarting or redeploying the web service does not reset the paper account or reprocess the last committed bar.
3. A persistence failure cannot silently reset state or fall back to local storage.
4. Runtime state, model, trade event, and audit event for one processed bar commit atomically.
5. Dashboard history and engine status recover after process restart.
6. Local file-backed usage remains available when no database URL is configured.
7. CI covers both file behavior and transactional Postgres behavior.
8. Live trading remains disabled.

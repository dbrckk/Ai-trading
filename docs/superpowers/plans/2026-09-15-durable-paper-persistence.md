# Durable Paper Persistence Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Persist the hosted paper-trading account, online River model, trade history, audit history, and runtime status in PostgreSQL so Render restarts and overlapping deploys cannot reset or double-commit paper state.

**Architecture:** Add a small persistence contract with file and PostgreSQL backends. `PaperAutonomousRuntime` will load one durable snapshot, compute one paper step, then commit state + model + optional trade + audit atomically through the facade; PostgreSQL uses a revision-checked transaction to resolve overlapping workers safely. The dashboard and hosted status path will use the same facade, while file-backed behavior remains the default when `AI_TRADING_DATABASE_URL` is absent.

**Tech Stack:** Python 3.11+, `psycopg[binary]>=3.2`, PostgreSQL 16 in GitHub Actions, existing `joblib`, `river`, `pytest`, `ruff`.

**Spec:** `docs/superpowers/specs/2026-09-15-durable-paper-persistence-design.md`

## Global Constraints

- Paper trading only; do not add live brokerage or real-money order routing.
- Existing risk checks, scheduler semantics, and trading decisions must remain unchanged.
- `AI_TRADING_DATABASE_URL` selects PostgreSQL; absence of that variable selects files.
- If `AI_TRADING_DATABASE_URL` is present and PostgreSQL fails, fail closed; never silently fall back to files.
- PostgreSQL is the production source of truth for runtime state, model, trades, audit history, and hosted status.
- One processed bar must persist state + model + optional trade + audit atomically.
- Overlapping hosted workers must not both commit the same starting revision.
- Model payload checksum must be verified before deserialization.
- Existing local artifact paths remain backward-compatible for file-backed usage.
- No destructive database migrations and no automatic import of legacy local artifacts.
- Secrets must never be written to Git, logs, dashboard HTML, runtime status payloads, or test snapshots.

---

## File Structure

Create these focused modules:

- `src/ai_trading/persistence.py` — persistence-domain dataclasses, protocol, runtime-key helper, commit outcome.
- `src/ai_trading/model_codec.py` — River model `joblib` byte serialization and SHA-256 verification.
- `src/ai_trading/file_persistence.py` — adapter over current JSON/JSONL/joblib/status files.
- `src/ai_trading/postgres_persistence.py` — schema initialization and transactional PostgreSQL backend.
- `src/ai_trading/persistence_factory.py` — environment-driven backend construction only.

Modify these existing modules:

- `src/ai_trading/audit.py` — expose reusable deterministic audit-record construction while preserving `AuditLog` behavior.
- `src/ai_trading/runtime.py` — use the persistence contract for load/commit instead of separate state/model/trade/audit writes.
- `src/ai_trading/hosted_runtime.py` — stable runtime key, injected persistence, durable hosted status.
- `src/ai_trading/dashboard.py` — read state/trades/status through persistence in hosted mode while retaining legacy render helpers for unit tests.
- `pyproject.toml` — add `psycopg[binary]>=3.2`.
- `.github/workflows/ci.yml` — add PostgreSQL 16 service and integration-test database URL.
- `README.md` — document durable PostgreSQL configuration and fail-closed behavior.

Create tests:

- `tests/test_model_codec.py`
- `tests/test_persistence_contract.py`
- `tests/test_file_persistence.py`
- `tests/test_postgres_persistence.py`
- `tests/test_runtime_persistence.py`
- `tests/test_hosted_persistence.py`

Reuse/adjust:

- `tests/test_runtime.py`
- `tests/test_trade_journal.py`
- `tests/test_runtime_status.py`
- `tests/test_dashboard.py`
- `tests/test_dashboard_engine_status.py`
- `tests/test_dashboard_health.py`
- `tests/test_hosted_runtime.py`

---

### Task 1: Define the persistence contract, runtime identity, and model codec

**Files:**
- Create: `src/ai_trading/persistence.py`
- Create: `src/ai_trading/model_codec.py`
- Modify: `src/ai_trading/audit.py`
- Test: `tests/test_persistence_contract.py`
- Test: `tests/test_model_codec.py`

**Interfaces:**
- Produces: `build_runtime_key(symbol: str, interval: str) -> str`
- Produces: `ModelBlob(format: str, version: int, payload: bytes, sha256: str)`
- Produces: `PersistedRuntime(state: RuntimeState, model: ModelBlob | None, revision: int, is_new: bool)`
- Produces: `RuntimeStepCommit(expected_revision: int, state: RuntimeState, model: ModelBlob, trade: TradeSnapshot | None, audit_event: str, audit_payload: dict[str, Any])`
- Produces: `CommitOutcome.COMMITTED` and `CommitOutcome.CONFLICT`
- Produces protocol methods `initialize_schema`, `load_runtime`, `commit_step`, `list_trades`, `save_runtime_status`, `load_runtime_status`.
- Produces: `serialize_model(model: RiverDirectionModel) -> ModelBlob`
- Produces: `deserialize_model(blob: ModelBlob) -> RiverDirectionModel`
- Produces: `build_audit_record(event: str, payload: dict[str, Any], prev_hash: str, *, timestamp_utc: str | None = None) -> dict[str, Any]`

- [ ] **Step 1: Write failing contract and runtime-key tests**

Create `tests/test_persistence_contract.py`:

```python
from ai_trading.persistence import CommitOutcome, build_runtime_key


def test_build_runtime_key_is_stable_and_market_specific() -> None:
    assert build_runtime_key("GC=F", "5m") == "paper:GC=F:5m:online-river:v1"
    assert build_runtime_key("SI=F", "5m") != build_runtime_key("GC=F", "5m")


def test_commit_outcome_has_explicit_conflict_state() -> None:
    assert CommitOutcome.COMMITTED.value == "committed"
    assert CommitOutcome.CONFLICT.value == "conflict"
```

- [ ] **Step 2: Run the contract tests and verify RED**

Run:

```bash
pytest tests/test_persistence_contract.py -q
```

Expected: collection/import failure because `ai_trading.persistence` does not exist.

- [ ] **Step 3: Add the minimal persistence-domain module**

Create `src/ai_trading/persistence.py` with these exact public shapes:

```python
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Protocol

from .runtime_state import RuntimeState
from .runtime_status import HostedRuntimeStatus
from .trade_journal import TradeSnapshot


@dataclass(frozen=True)
class ModelBlob:
    format: str
    version: int
    payload: bytes
    sha256: str


@dataclass(frozen=True)
class PersistedRuntime:
    state: RuntimeState
    model: ModelBlob | None
    revision: int
    is_new: bool


@dataclass(frozen=True)
class RuntimeStepCommit:
    expected_revision: int
    state: RuntimeState
    model: ModelBlob
    trade: TradeSnapshot | None
    audit_event: str
    audit_payload: dict[str, Any]


class CommitOutcome(str, Enum):
    COMMITTED = "committed"
    CONFLICT = "conflict"


def build_runtime_key(symbol: str, interval: str) -> str:
    return f"paper:{symbol}:{interval}:online-river:v1"


class PaperPersistence(Protocol):
    def initialize_schema(self) -> None: ...

    def load_runtime(self, runtime_key: str, starting_cash: float) -> PersistedRuntime: ...

    def commit_step(self, runtime_key: str, commit: RuntimeStepCommit) -> CommitOutcome: ...

    def list_trades(
        self,
        runtime_key: str | None = None,
        *,
        limit: int | None = None,
    ) -> tuple[TradeSnapshot, ...]: ...

    def save_runtime_status(self, runtime_key: str, status: HostedRuntimeStatus) -> None: ...

    def load_runtime_status(self, runtime_key: str) -> HostedRuntimeStatus | None: ...
```

- [ ] **Step 4: Run the contract tests and verify GREEN**

Run:

```bash
pytest tests/test_persistence_contract.py -q
```

Expected: 2 passed.

- [ ] **Step 5: Write failing model serialization tests**

Create `tests/test_model_codec.py`:

```python
from dataclasses import replace

import pytest

from ai_trading.model_codec import deserialize_model, serialize_model
from ai_trading.online import RiverDirectionModel


def test_model_codec_round_trips_river_model() -> None:
    model = RiverDirectionModel()
    model.learn_one({"return_1": 0.01}, 1)

    blob = serialize_model(model)
    restored = deserialize_model(blob)

    assert blob.format == "joblib-river-v1"
    assert blob.version == 1
    assert len(blob.sha256) == 64
    assert type(restored) is RiverDirectionModel


def test_model_codec_rejects_corrupt_payload() -> None:
    blob = serialize_model(RiverDirectionModel())
    corrupt = replace(blob, payload=blob.payload + b"corrupt")

    with pytest.raises(ValueError, match="checksum"):
        deserialize_model(corrupt)


def test_model_codec_rejects_unknown_version() -> None:
    blob = serialize_model(RiverDirectionModel())

    with pytest.raises(ValueError, match="format/version"):
        deserialize_model(replace(blob, version=99))
```

If `RiverDirectionModel.learn_one` requires the full feature vector, remove the `learn_one` call; the round-trip assertion is about serialization identity, not predictive quality.

- [ ] **Step 6: Run codec tests and verify RED**

Run:

```bash
pytest tests/test_model_codec.py -q
```

Expected: import failure because `ai_trading.model_codec` does not exist.

- [ ] **Step 7: Implement byte serialization with checksum verification**

Create `src/ai_trading/model_codec.py`:

```python
from __future__ import annotations

import hashlib
from io import BytesIO

import joblib

from .online import RiverDirectionModel
from .persistence import ModelBlob

MODEL_FORMAT = "joblib-river-v1"
MODEL_VERSION = 1


def serialize_model(model: RiverDirectionModel) -> ModelBlob:
    buffer = BytesIO()
    joblib.dump(model, buffer)
    payload = buffer.getvalue()
    return ModelBlob(
        format=MODEL_FORMAT,
        version=MODEL_VERSION,
        payload=payload,
        sha256=hashlib.sha256(payload).hexdigest(),
    )


def deserialize_model(blob: ModelBlob) -> RiverDirectionModel:
    if blob.format != MODEL_FORMAT or blob.version != MODEL_VERSION:
        raise ValueError("unsupported model format/version")
    actual = hashlib.sha256(blob.payload).hexdigest()
    if actual != blob.sha256:
        raise ValueError("model checksum mismatch")
    model = joblib.load(BytesIO(blob.payload))
    if not isinstance(model, RiverDirectionModel):
        raise ValueError("persisted model has unexpected type")
    return model
```

- [ ] **Step 8: Run codec tests and verify GREEN**

Run:

```bash
pytest tests/test_model_codec.py -q
```

Expected: all tests pass.

- [ ] **Step 9: Write a failing reusable-audit-record test**

Add to a new or existing audit test:

```python
from ai_trading.audit import build_audit_record


def test_build_audit_record_is_hash_chained() -> None:
    record = build_audit_record(
        "runtime_step",
        {"processed_bars": 3},
        "GENESIS",
        timestamp_utc="2026-09-15T00:00:00+00:00",
    )
    assert record["prev_hash"] == "GENESIS"
    assert len(record["hash"]) == 64
```

- [ ] **Step 10: Refactor `AuditLog.append` through `build_audit_record` and rerun audit tests**

In `src/ai_trading/audit.py`, retain the current canonical SHA-256 algorithm and add:

```python
def build_audit_record(
    event: str,
    payload: dict[str, Any],
    prev_hash: str,
    *,
    timestamp_utc: str | None = None,
) -> dict[str, Any]:
    body = {
        "timestamp_utc": timestamp_utc or datetime.now(UTC).isoformat(),
        "event": event,
        "payload": payload,
        "prev_hash": prev_hash,
    }
    return {**body, "hash": _record_hash(body)}
```

Change `AuditLog.append` to call this helper with `self._last_hash()` and then append the returned record unchanged.

Run:

```bash
pytest tests -q -k audit
```

Expected: all audit tests pass.

- [ ] **Step 11: Commit Task 1**

```bash
git add src/ai_trading/persistence.py src/ai_trading/model_codec.py src/ai_trading/audit.py tests/test_persistence_contract.py tests/test_model_codec.py tests

git commit -m "feat: define durable persistence contract"
```

---

### Task 2: Add the backward-compatible file persistence backend and factory

**Files:**
- Create: `src/ai_trading/file_persistence.py`
- Create: `src/ai_trading/persistence_factory.py`
- Modify: `pyproject.toml`
- Test: `tests/test_file_persistence.py`
- Test: `tests/test_persistence_contract.py`

**Interfaces:**
- Consumes: `PaperPersistence`, `PersistedRuntime`, `RuntimeStepCommit`, `CommitOutcome`, `ModelBlob`.
- Produces: `FilePaperPersistence`.
- Produces: `build_persistence_from_env() -> PaperPersistence`.
- Postgres import in the factory must be lazy enough that local file-only use remains straightforward.

- [ ] **Step 1: Write failing file-backend compatibility tests**

Create `tests/test_file_persistence.py`:

```python
from ai_trading.file_persistence import FilePaperPersistence
from ai_trading.model_codec import serialize_model
from ai_trading.online import RiverDirectionModel
from ai_trading.persistence import CommitOutcome, RuntimeStepCommit
from ai_trading.runtime_state import RuntimeState
from ai_trading.runtime_status import HostedRuntimeStatus
from ai_trading.trade_journal import TradeSnapshot


def _state(cash: float = 100_000.0, bars: int = 0) -> RuntimeState:
    return RuntimeState(
        cash=cash,
        units=0.0,
        last_price=0.0,
        peak_equity=cash,
        day_start_equity=cash,
        processed_bars=bars,
    )


def test_file_persistence_round_trip_survives_new_instance(tmp_path) -> None:
    persistence = FilePaperPersistence(root=tmp_path)
    loaded = persistence.load_runtime("paper:GC=F:5m:online-river:v1", 100_000.0)
    assert loaded.is_new is True

    outcome = persistence.commit_step(
        "paper:GC=F:5m:online-river:v1",
        RuntimeStepCommit(
            expected_revision=loaded.revision,
            state=_state(99_900.0, bars=1),
            model=serialize_model(RiverDirectionModel()),
            trade=TradeSnapshot(
                timestamp_utc="2026-09-15T10:00:00+00:00",
                symbol="GC=F",
                side="BUY",
                quantity=1.0,
                price=100.0,
                status="PAPER_FILLED",
                strategy="online-river",
            ),
            audit_event="runtime_step",
            audit_payload={"processed_bars": 1},
        ),
    )
    assert outcome is CommitOutcome.COMMITTED

    restored = FilePaperPersistence(root=tmp_path).load_runtime(
        "paper:GC=F:5m:online-river:v1",
        100_000.0,
    )
    assert restored.state.cash == 99_900.0
    assert restored.state.processed_bars == 1
    assert restored.model is not None
    assert restored.revision == 1


def test_file_persistence_status_round_trip(tmp_path) -> None:
    persistence = FilePaperPersistence(root=tmp_path)
    status = HostedRuntimeStatus(
        engine_status="RUNNING",
        symbol="GC=F",
        interval="5m",
        updated_at_utc="2026-09-15T10:00:00+00:00",
    )
    key = "paper:GC=F:5m:online-river:v1"
    persistence.save_runtime_status(key, status)
    assert persistence.load_runtime_status(key) == status
```

- [ ] **Step 2: Verify RED**

Run:

```bash
pytest tests/test_file_persistence.py -q
```

Expected: import failure because `FilePaperPersistence` does not exist.

- [ ] **Step 3: Implement `FilePaperPersistence` using existing file formats**

Create `src/ai_trading/file_persistence.py` with defaults rooted under `artifacts/` and these path mappings:

```python
self.state_store = RuntimeStateStore(root / "runtime_state.json")
self.trade_journal = TradeJournal(root / "trades.jsonl")
self.audit_log = AuditLog(root / "audit.jsonl")
self.status_store = HostedRuntimeStatusStore(root / "runtime_status.json")
self.model_path = root / "models" / "online-river.joblib"
```

Implementation rules:

```python
def initialize_schema(self) -> None:
    return None
```

`load_runtime` must use `RuntimeStateStore.load(starting_cash)`, read `model_path` as raw bytes when present, compute its SHA-256, wrap it as `ModelBlob(format="joblib-river-v1", version=1, ...)`, and return `revision=state.processed_bars`. `is_new` is true only when the state file did not exist before loading.

`commit_step` must reject mismatched `expected_revision` by returning `CommitOutcome.CONFLICT`, then write optional trade, audit, runtime state, and model bytes. Write model bytes atomically with a `.tmp` file and `replace`. Return `COMMITTED`.

`list_trades`, `save_runtime_status`, and `load_runtime_status` delegate to the existing stores. The `runtime_key` is ignored by the legacy file backend because it preserves the current one-runtime-per-artifact-directory behavior.

- [ ] **Step 4: Verify GREEN plus backward compatibility**

Run:

```bash
pytest tests/test_file_persistence.py tests/test_runtime_state.py tests/test_trade_journal.py tests/test_runtime_status.py -q
```

Expected: all tests pass.

- [ ] **Step 5: Write failing factory-selection tests**

Add to `tests/test_persistence_contract.py`:

```python
from ai_trading.file_persistence import FilePaperPersistence
from ai_trading.persistence_factory import build_persistence_from_env


def test_factory_uses_file_backend_without_database_url(monkeypatch, tmp_path) -> None:
    monkeypatch.delenv("AI_TRADING_DATABASE_URL", raising=False)
    persistence = build_persistence_from_env(file_root=tmp_path)
    assert isinstance(persistence, FilePaperPersistence)
```

Add a second test that monkeypatches `PostgresPaperPersistence` in the factory module, sets `AI_TRADING_DATABASE_URL=postgresql://example`, and asserts the PostgreSQL backend receives the URL and `initialize_schema()` is called exactly once.

- [ ] **Step 6: Add PostgreSQL dependency and minimal environment factory**

Modify `pyproject.toml` dependencies:

```toml
"psycopg[binary]>=3.2"
```

Create `src/ai_trading/persistence_factory.py`:

```python
from __future__ import annotations

import os
from pathlib import Path

from .file_persistence import FilePaperPersistence
from .persistence import PaperPersistence
from .postgres_persistence import PostgresPaperPersistence


def build_persistence_from_env(
    *,
    file_root: str | Path = "artifacts",
) -> PaperPersistence:
    database_url = os.getenv("AI_TRADING_DATABASE_URL", "").strip()
    if not database_url:
        return FilePaperPersistence(root=file_root)
    persistence = PostgresPaperPersistence(database_url)
    persistence.initialize_schema()
    return persistence
```

The factory must not catch PostgreSQL connection/schema exceptions.

- [ ] **Step 7: Run factory/file tests**

Run:

```bash
pytest tests/test_persistence_contract.py tests/test_file_persistence.py -q
```

Expected: all tests pass.

- [ ] **Step 8: Commit Task 2**

```bash
git add pyproject.toml src/ai_trading/file_persistence.py src/ai_trading/persistence_factory.py tests/test_file_persistence.py tests/test_persistence_contract.py

git commit -m "feat: add file persistence facade"
```

---

### Task 3: Implement the PostgreSQL schema and durable backend

**Files:**
- Create: `src/ai_trading/postgres_persistence.py`
- Test: `tests/test_postgres_persistence.py`

**Interfaces:**
- Consumes: all contract dataclasses from `persistence.py` and `build_audit_record`.
- Produces: `PostgresPaperPersistence(database_url: str)` implementing `PaperPersistence`.
- Uses one short-lived psycopg connection per public persistence operation; no connection object is shared between dashboard and worker threads.

- [ ] **Step 1: Write PostgreSQL test fixture and failing schema-idempotency test**

Create `tests/test_postgres_persistence.py` with module-level skip when `TEST_DATABASE_URL` is absent:

```python
import os
import uuid

import pytest

from ai_trading.postgres_persistence import PostgresPaperPersistence

TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL")
pytestmark = pytest.mark.skipif(
    not TEST_DATABASE_URL,
    reason="TEST_DATABASE_URL is not configured",
)


@pytest.fixture
def persistence():
    assert TEST_DATABASE_URL is not None
    backend = PostgresPaperPersistence(TEST_DATABASE_URL)
    backend.initialize_schema()
    return backend


def runtime_key() -> str:
    return f"paper:test:{uuid.uuid4()}:5m:online-river:v1"


def test_schema_initialization_is_idempotent(persistence) -> None:
    persistence.initialize_schema()
    persistence.initialize_schema()
```

- [ ] **Step 2: Run the integration test and verify RED**

Local command with a PostgreSQL test URL:

```bash
TEST_DATABASE_URL="postgresql://postgres:postgres@127.0.0.1:5432/ai_trading_test" pytest tests/test_postgres_persistence.py -q
```

Expected: import failure because `PostgresPaperPersistence` does not exist.

- [ ] **Step 3: Implement idempotent schema creation**

Create `src/ai_trading/postgres_persistence.py`. `initialize_schema()` must execute `CREATE TABLE IF NOT EXISTS` statements for exactly these tables/columns from the spec:

```sql
CREATE TABLE IF NOT EXISTS paper_runtime_state (
    runtime_key text PRIMARY KEY,
    cash double precision NOT NULL,
    units double precision NOT NULL,
    last_price double precision NOT NULL,
    peak_equity double precision NOT NULL,
    day_start_equity double precision NOT NULL,
    last_processed text NULL,
    processed_bars bigint NOT NULL,
    last_learning_cycle_bar bigint NOT NULL,
    revision bigint NOT NULL DEFAULT 0,
    updated_at timestamptz NOT NULL DEFAULT now()
);
```

```sql
CREATE TABLE IF NOT EXISTS paper_model_state (
    runtime_key text PRIMARY KEY REFERENCES paper_runtime_state(runtime_key) ON DELETE CASCADE,
    format text NOT NULL,
    version integer NOT NULL,
    payload bytea NOT NULL,
    sha256 text NOT NULL,
    updated_at timestamptz NOT NULL DEFAULT now()
);
```

```sql
CREATE TABLE IF NOT EXISTS paper_trades (
    id bigserial PRIMARY KEY,
    runtime_key text NOT NULL,
    event_key text NOT NULL,
    timestamp_utc text NOT NULL,
    symbol text NOT NULL,
    side text NOT NULL,
    quantity double precision NOT NULL,
    price double precision NOT NULL,
    status text NOT NULL,
    pnl double precision NOT NULL DEFAULT 0,
    confidence double precision NULL,
    strategy text NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (runtime_key, event_key)
);
```

```sql
CREATE TABLE IF NOT EXISTS paper_audit_events (
    id bigserial PRIMARY KEY,
    runtime_key text NOT NULL,
    timestamp_utc timestamptz NOT NULL,
    event text NOT NULL,
    payload jsonb NOT NULL,
    prev_hash text NOT NULL,
    hash text NOT NULL,
    UNIQUE (runtime_key, hash)
);
```

```sql
CREATE TABLE IF NOT EXISTS paper_runtime_status (
    runtime_key text PRIMARY KEY,
    engine_status text NOT NULL,
    symbol text NOT NULL,
    interval text NOT NULL,
    updated_at_utc timestamptz NOT NULL,
    payload jsonb NOT NULL
);
```

Also create indexes:

```sql
CREATE INDEX IF NOT EXISTS idx_paper_trades_runtime_id
ON paper_trades(runtime_key, id DESC);

CREATE INDEX IF NOT EXISTS idx_paper_audit_runtime_id
ON paper_audit_events(runtime_key, id DESC);
```

Do not print the database URL.

- [ ] **Step 4: Verify schema GREEN**

Run the Step 2 command again.

Expected: schema test passes.

- [ ] **Step 5: Add failing restart-survival tests for state/model/trades/status**

Add tests that:

1. call `load_runtime(key, 100_000.0)` and assert `is_new`, revision `0`;
2. commit state with processed bars `1`, a serialized model, one trade and one audit event;
3. construct a second `PostgresPaperPersistence(TEST_DATABASE_URL)`;
4. assert state values, revision `1`, model checksum, trade list and runtime status all survive the new backend instance.

Use a unique `runtime_key()` per test to avoid cross-test deletion requirements.

- [ ] **Step 6: Implement `load_runtime`, trade event keys, trade listing, and durable status**

`load_runtime` must first ensure a row exists using:

```sql
INSERT INTO paper_runtime_state (
    runtime_key, cash, units, last_price, peak_equity,
    day_start_equity, last_processed, processed_bars,
    last_learning_cycle_bar, revision
)
VALUES (%s, %s, 0, 0, %s, %s, NULL, 0, 0, 0)
ON CONFLICT (runtime_key) DO NOTHING;
```

Then select state + revision and left-join model state. `is_new` is determined from whether the insert created the runtime row, not from balances or counters.

Create a private deterministic trade event key from the immutable serialized fields:

```python
canonical = json.dumps(asdict(trade), sort_keys=True, separators=(",", ":"))
event_key = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
```

`list_trades` must return chronological order matching `TradeJournal.list`: query newest first when limiting, then reverse the rows in Python before returning them.

`save_runtime_status` uses `INSERT ... ON CONFLICT (runtime_key) DO UPDATE`; store the complete dataclass as JSON payload but also keep engine/symbol/interval/timestamp in dedicated columns. `load_runtime_status` reconstructs `HostedRuntimeStatus` from payload.

- [ ] **Step 7: Add failing atomicity and concurrency tests**

Add these explicit tests:

```python
def test_same_expected_revision_has_exactly_one_winner(persistence) -> None:
    key = runtime_key()
    loaded = persistence.load_runtime(key, 100_000.0)
    first = make_commit(expected_revision=loaded.revision, processed_bars=1)
    second = make_commit(expected_revision=loaded.revision, processed_bars=1)

    assert persistence.commit_step(key, first) is CommitOutcome.COMMITTED
    assert persistence.commit_step(key, second) is CommitOutcome.CONFLICT
    assert persistence.load_runtime(key, 100_000.0).revision == 1
```

Add a forced-failure test by exposing only a test-only hook through dependency injection, not production flags: constructor argument `before_state_commit: Callable[[], None] | None = None`. In the test, raise `RuntimeError("forced rollback")` after trade/model/audit writes but before final state update, then assert the transaction leaves no trade/audit/model changes and the state revision is unchanged.

- [ ] **Step 8: Implement the revision-checked transaction**

`commit_step` must run inside one psycopg transaction:

1. `SELECT revision FROM paper_runtime_state WHERE runtime_key = %s FOR UPDATE`;
2. if row missing, raise `RuntimeError("runtime state missing")`;
3. if stored revision differs from `commit.expected_revision`, return `CommitOutcome.CONFLICT` without writes;
4. insert optional trade with deterministic event key;
5. read the latest committed audit hash for this runtime inside the same transaction, default `GENESIS`, build the audit record with `build_audit_record`, insert it;
6. upsert `paper_model_state`;
7. invoke `before_state_commit()` only when the injected test hook is non-`None`;
8. update `paper_runtime_state` with all state fields and `revision = revision + 1 WHERE runtime_key = %s AND revision = %s`;
9. require `cursor.rowcount == 1`; otherwise raise a transaction error;
10. let the connection context commit.

The conflict path must exit before trade/audit/model writes. Genuine psycopg exceptions propagate.

- [ ] **Step 9: Run full PostgreSQL integration tests**

Run:

```bash
TEST_DATABASE_URL="postgresql://postgres:postgres@127.0.0.1:5432/ai_trading_test" pytest tests/test_postgres_persistence.py -q
```

Expected: all PostgreSQL persistence tests pass.

- [ ] **Step 10: Commit Task 3**

```bash
git add src/ai_trading/postgres_persistence.py tests/test_postgres_persistence.py

git commit -m "feat: add transactional postgres persistence"
```

---

### Task 4: Move `PaperAutonomousRuntime` behind the persistence transaction

**Files:**
- Modify: `src/ai_trading/runtime.py`
- Test: `tests/test_runtime_persistence.py`
- Modify as needed: `tests/test_runtime.py`

**Interfaces:**
- Consumes: `PaperPersistence`, `PersistedRuntime`, `RuntimeStepCommit`, `CommitOutcome`, model codec.
- Produces: persistence-aware `PaperAutonomousRuntime(..., persistence: PaperPersistence | None = None, runtime_key: str | None = None, ...)`.
- Existing constructor arguments for file paths/stores remain accepted so current tests and local callers do not break abruptly.

- [ ] **Step 1: Write a failing test proving runtime commits through one facade call**

Create `tests/test_runtime_persistence.py` with a small in-memory fake implementing the protocol. The fake records `commit_step` calls. Reuse an existing deterministic dataframe fixture from runtime tests. Assert one processed step produces exactly one `RuntimeStepCommit` containing:

- incremented `RuntimeState.processed_bars`;
- a `ModelBlob`;
- optional trade when rebalance changes units;
- `audit_event == "runtime_step"`;
- audit payload containing execution time, prediction, risk decision, equity, units, processed bars, retrain flag.

- [ ] **Step 2: Run and verify RED**

```bash
pytest tests/test_runtime_persistence.py -q
```

Expected: constructor or behavior failure because runtime does not use persistence yet.

- [ ] **Step 3: Refactor runtime loading without changing trading decisions**

In `PaperAutonomousRuntime.__init__`:

- accept optional `persistence` and `runtime_key`;
- when `persistence` is provided, require a non-empty `runtime_key`;
- when it is absent, construct `FilePaperPersistence` from the legacy stores/paths so existing callers still get file behavior.

Replace separate state/model load with:

```python
persisted = self.persistence.load_runtime(
    self.runtime_key,
    self.risk_config.starting_cash,
)
state = persisted.state
if persisted.model is None:
    if not persisted.is_new and state.processed_bars > 0:
        raise ValueError("persisted runtime is missing its online model")
    model = RiverDirectionModel()
else:
    model = deserialize_model(persisted.model)
```

Keep the duplicate-bar check before learning/prediction exactly as today.

- [ ] **Step 4: Replace independent writes with one `commit_step`**

Keep the existing prediction, risk evaluation, paper broker rebalance, and state construction. Instead of writing trade/state/model/audit independently, build:

```python
commit = RuntimeStepCommit(
    expected_revision=persisted.revision,
    state=new_state,
    model=serialize_model(model),
    trade=trade_snapshot,
    audit_event="runtime_step",
    audit_payload={
        "signal_time": str(signal_idx),
        "execution_time": execution_time,
        "prediction": asdict(prediction),
        "risk_decision": asdict(decision),
        "equity": broker.state.equity,
        "units": broker.state.units,
        "processed_bars": processed_bars,
        "retrain_due": retrain_due,
    },
)
outcome = self.persistence.commit_step(self.runtime_key, commit)
```

If outcome is `CONFLICT`, return a non-processed `RuntimeStepResult` with:

```python
processed=False
approved=False
reason="persistence revision conflict"
retrain_due=False
```

Use the pre-commit broker equity/units only for observability; do not retry or write any local recovery state inside that iteration.

- [ ] **Step 5: Run targeted runtime tests**

```bash
pytest tests/test_runtime_persistence.py tests/test_runtime.py -q
```

Expected: all pass and existing paper decision behavior remains unchanged.

- [ ] **Step 6: Run trade/audit regression tests**

```bash
pytest tests/test_trade_journal.py tests -q -k "audit or runtime"
```

Expected: all selected tests pass.

- [ ] **Step 7: Commit Task 4**

```bash
git add src/ai_trading/runtime.py tests/test_runtime_persistence.py tests/test_runtime.py

git commit -m "refactor: commit paper runtime state atomically"
```

---

### Task 5: Route hosted worker status and dashboard reads through durable persistence

**Files:**
- Modify: `src/ai_trading/hosted_runtime.py`
- Modify: `src/ai_trading/dashboard.py`
- Test: `tests/test_hosted_persistence.py`
- Modify: `tests/test_hosted_runtime.py`
- Modify: `tests/test_dashboard.py`
- Modify: `tests/test_dashboard_engine_status.py`
- Modify: `tests/test_dashboard_health.py`

**Interfaces:**
- Consumes: `build_runtime_key`, `build_persistence_from_env`, `PaperPersistence`.
- Produces: hosted runtime and dashboard sharing the same selected persistence backend and runtime key.

- [ ] **Step 1: Write failing hosted wiring tests**

Create `tests/test_hosted_persistence.py` with a fake persistence and assert:

1. `HostedPaperSettings(symbol="GC=F", interval="5m").runtime_key == "paper:GC=F:5m:online-river:v1"`;
2. `run_hosted_paper_loop(settings, persistence=fake)` constructs `PaperAutonomousRuntime` with that persistence and key;
3. STARTING/RUNNING/ERROR status calls use `fake.save_runtime_status(runtime_key, status)` rather than directly constructing `HostedRuntimeStatusStore`.

- [ ] **Step 2: Verify RED**

```bash
pytest tests/test_hosted_persistence.py -q
```

Expected: missing property/parameters.

- [ ] **Step 3: Refactor hosted runtime injection**

Add:

```python
@property
def runtime_key(self) -> str:
    return build_runtime_key(self.symbol, self.interval)
```

Change signatures to:

```python
def run_hosted_paper_loop(
    settings: HostedPaperSettings,
    *,
    persistence: PaperPersistence | None = None,
) -> None:
```

and

```python
def start_hosted_paper_runtime(
    *,
    settings: HostedPaperSettings | None = None,
    persistence: PaperPersistence | None = None,
    runner: Callable[..., None] = run_hosted_paper_loop,
) -> Thread | None:
```

When persistence is absent, build it once through `build_persistence_from_env()`. Pass the same object and `settings.runtime_key` into `PaperAutonomousRuntime`. Replace status-store writes with persistence status writes.

A PostgreSQL/schema exception must propagate out before scheduling bars. The worker error handler should attempt to save `ERROR`; if storage itself is unavailable, log the original exception without resetting state.

- [ ] **Step 4: Write failing dashboard-persistence tests**

Add a fake persistence exposing a known state, trade tuple, and runtime status. Test `render_dashboard(..., persistence=fake, runtime_key=key)` shows those values even when local files are empty. Add a failure fake whose `load_runtime` raises `RuntimeError("storage unavailable")`; assert the dashboard does not display a synthetic `100,000.00` account and `/api/status` reports an explicit storage error state.

- [ ] **Step 5: Refactor dashboard hosted path**

Extend `render_dashboard` with optional keyword arguments:

```python
persistence: PaperPersistence | None = None
runtime_key: str | None = None
```

When both are supplied:

- `persistence.list_trades(runtime_key, limit=200)` is the trade source;
- `persistence.load_runtime(runtime_key, starting_cash).state` is the account source;
- `persistence.load_runtime_status(runtime_key)` is the engine-status source.

When not supplied, preserve the existing `TradeJournal`/`RuntimeStateStore`/`HostedRuntimeStatusStore` path so current direct-render tests remain compatible.

In `serve_dashboard`, read `HostedPaperSettings.from_env()` once, build persistence once, derive runtime key once, start the worker with those objects, and make handlers use that same persistence/key.

For storage read failures, return JSON from `/api/status` such as:

```json
{
  "engine_status": "ERROR",
  "engine_healthy": false,
  "storage_healthy": false,
  "error": "storage unavailable"
}
```

Do not include exception repr if it could expose a connection string; use a constant public error message and log only exception type plus safe text.

`/healthz` remains HTTP 200 for web liveness and returns:

```json
{
  "web_healthy": true,
  "engine_healthy": false,
  "engine_status": "ERROR"
}
```

when storage is unavailable.

- [ ] **Step 6: Run hosted/dashboard tests**

```bash
pytest tests/test_hosted_persistence.py tests/test_hosted_runtime.py tests/test_dashboard.py tests/test_dashboard_engine_status.py tests/test_dashboard_health.py -q
```

Expected: all pass.

- [ ] **Step 7: Commit Task 5**

```bash
git add src/ai_trading/hosted_runtime.py src/ai_trading/dashboard.py tests/test_hosted_persistence.py tests/test_hosted_runtime.py tests/test_dashboard.py tests/test_dashboard_engine_status.py tests/test_dashboard_health.py

git commit -m "feat: use durable persistence in hosted dashboard"
```

---

### Task 6: Add PostgreSQL CI coverage and complete regression verification

**Files:**
- Modify: `.github/workflows/ci.yml`
- Modify: `tests/test_postgres_persistence.py` only if CI exposes a portability issue.

**Interfaces:**
- Produces: reproducible PostgreSQL 16 integration environment for every PR to `main`.
- No Supabase secret is consumed in CI.

- [ ] **Step 1: Add PostgreSQL service to the existing CI job**

Under `jobs.test`, add:

```yaml
services:
  postgres:
    image: postgres:16
    env:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
      POSTGRES_DB: ai_trading_test
    ports:
      - 5432:5432
    options: >-
      --health-cmd "pg_isready -U postgres -d ai_trading_test"
      --health-interval 5s
      --health-timeout 5s
      --health-retries 10
```

Add job-level environment:

```yaml
env:
  TEST_DATABASE_URL: postgresql://postgres:postgres@127.0.0.1:5432/ai_trading_test
```

Keep Python 3.11, Ruff, and `pytest -q` unchanged.

- [ ] **Step 2: Run workflow-equivalent commands locally**

With PostgreSQL 16 available locally:

```bash
python -m pip install -e ".[dev]"
ruff check src tests
TEST_DATABASE_URL="postgresql://postgres:postgres@127.0.0.1:5432/ai_trading_test" pytest -q
```

Expected: Ruff exits 0 and Pytest reports 0 failed.

- [ ] **Step 3: Commit CI integration**

```bash
git add .github/workflows/ci.yml tests/test_postgres_persistence.py

git commit -m "ci: verify postgres persistence transactions"
```

- [ ] **Step 4: Open a PR and require the real GitHub Actions run to pass before merge**

PR body must state:

```text
Adds durable PostgreSQL persistence for paper runtime state, model, trades, audit history, and hosted status. Includes revision-based overlap protection and keeps file-backed local behavior when AI_TRADING_DATABASE_URL is absent. Live trading remains disabled.
```

Do not merge while Ruff, Pytest, or PostgreSQL integration tests are failing.

---

### Task 7: Document production configuration and perform a persistence restart proof

**Files:**
- Modify: `README.md`
- No source-code changes unless restart verification reveals a defect; any defect starts a new failing test before a fix.

**Interfaces:**
- Consumes: merged PostgreSQL persistence implementation.
- Produces: exact operator procedure for Supabase + Render and evidence that a restart preserves durable state.

- [ ] **Step 1: Add README configuration section**

Document:

```text
AI_TRADING_DATABASE_URL=<PostgreSQL connection string with TLS enabled>
```

State explicitly:

- hosted production uses PostgreSQL when this variable exists;
- no variable means file-backed local mode;
- invalid/unreachable PostgreSQL fails closed and does not reset the paper account;
- the connection string must not be committed;
- Supabase session-pooler connection strings are suitable when they include the provider-required TLS settings;
- live order routing is still absent.

- [ ] **Step 2: Verify documentation does not contain credentials**

Run:

```bash
grep -R "AI_TRADING_DATABASE_URL=" README.md docs/superpowers | cat
```

Expected: only placeholder/example text, no real hostname password or secret token.

- [ ] **Step 3: Configure Render only after a real Supabase PostgreSQL URL is available**

Set one environment variable on the existing `ai-trading-dashboard` service:

```text
AI_TRADING_DATABASE_URL=<the Supabase PostgreSQL connection string>
```

Do not replace unrelated Render environment variables. Do not paste the secret into GitHub issues, PRs, logs, README, or chat-visible status summaries.

- [ ] **Step 4: Verify first durable startup**

After Render auto-deploys/restarts, verify logs contain safe high-level startup messages only and no database URL. Query `/api/status` and dashboard to establish baseline values for:

- runtime key;
- processed bar count;
- cash/equity/units;
- latest trade count;
- engine status.

- [ ] **Step 5: Prove restart persistence**

Trigger one controlled redeploy/restart only after at least one durable runtime state exists. After the new process is live, verify:

1. `processed_bars` is not reset to `0` unless it was `0` before restart;
2. cash/units/equity match the last durable state before any new market bar processes;
3. previous trades still appear;
4. the online model loads without checksum/version errors;
5. the last committed `last_processed` bar is not committed a second time;
6. runtime status resumes under the same `runtime_key`.

- [ ] **Step 6: Run final verification before declaring completion**

```bash
ruff check src tests
TEST_DATABASE_URL="postgresql://postgres:postgres@127.0.0.1:5432/ai_trading_test" pytest -q
```

Then confirm the merged GitHub Actions workflow is green and the Render deploy is `live`.

- [ ] **Step 7: Commit documentation if not already included in the implementation PR**

```bash
git add README.md

git commit -m "docs: explain durable paper persistence"
```

---

## Final Requirement Traceability

- PostgreSQL source of truth: Tasks 3–5.
- State/model/trade/audit atomicity: Task 3.
- Overlapping deploy protection: Task 3 + runtime conflict handling in Task 4.
- Dashboard/status recovery: Task 5.
- File fallback compatibility: Task 2.
- Fail-closed PostgreSQL behavior: Tasks 2, 4, and 5.
- Checksum/version validation: Task 1.
- CI PostgreSQL transaction coverage: Task 6.
- Restart/redeploy proof: Task 7.
- Paper-only safety: global constraint enforced throughout; no task adds broker routing.

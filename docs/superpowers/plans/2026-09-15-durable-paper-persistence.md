# Durable Paper Persistence Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Persist paper account state, the online River model, trades, audit history, and hosted runtime status in PostgreSQL so Render restarts and overlapping deploys cannot reset or double-commit paper state.

**Architecture:** Add one `PaperPersistence` contract with file and PostgreSQL implementations. `PaperAutonomousRuntime` loads a durable snapshot, computes one paper step, then commits runtime state + model + optional trade + audit atomically; PostgreSQL resolves overlapping workers with a revision-checked transaction. The hosted dashboard reads from the same selected backend, while file-backed behavior remains the default when `AI_TRADING_DATABASE_URL` is absent.

**Tech Stack:** Python 3.11+, `psycopg[binary]>=3.2`, PostgreSQL 16 in GitHub Actions, existing `joblib`, `river`, `pytest`, `ruff`.

**Spec:** `docs/superpowers/specs/2026-09-15-durable-paper-persistence-design.md`

## Global Constraints

- Paper trading only; do not add live brokerage or real-money order routing.
- Existing risk checks, scheduler semantics, and trading decisions remain unchanged.
- `AI_TRADING_DATABASE_URL` present => PostgreSQL only; absent => file backend.
- PostgreSQL failure must fail closed; never silently fall back to files.
- One processed bar persists state + model + optional trade + audit atomically.
- Two workers starting from the same revision cannot both commit.
- Model payload checksum/version must be verified before deserialization.
- Existing artifact paths remain compatible for file-backed usage.
- No destructive migration and no automatic legacy-artifact import.
- Secrets never enter Git, logs, HTML, status JSON, or tests.

---

## File Map

Create:

- `src/ai_trading/persistence.py` — protocol and persistence-domain types.
- `src/ai_trading/model_codec.py` — model bytes + SHA-256 verification.
- `src/ai_trading/file_persistence.py` — adapter over existing file stores.
- `src/ai_trading/postgres_persistence.py` — schema + transactional backend.
- `src/ai_trading/persistence_factory.py` — env-based backend selection.
- `tests/test_persistence_contract.py`
- `tests/test_model_codec.py`
- `tests/test_file_persistence.py`
- `tests/test_postgres_persistence.py`
- `tests/test_runtime_persistence.py`
- `tests/test_hosted_persistence.py`

Modify:

- `src/ai_trading/audit.py`
- `src/ai_trading/runtime.py`
- `src/ai_trading/hosted_runtime.py`
- `src/ai_trading/dashboard.py`
- `pyproject.toml`
- `.github/workflows/ci.yml`
- `README.md`
- existing runtime/dashboard tests where constructor wiring changes.

---

### Task 1: Persistence domain, runtime key, audit helper, and model codec

**Files:**
- Create: `src/ai_trading/persistence.py`
- Create: `src/ai_trading/model_codec.py`
- Modify: `src/ai_trading/audit.py`
- Create: `tests/test_persistence_contract.py`
- Create: `tests/test_model_codec.py`

**Interfaces produced:**

```python
class CommitOutcome(str, Enum):
    COMMITTED = "committed"
    CONFLICT = "conflict"

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

class PaperPersistence(Protocol):
    def initialize_schema(self) -> None: ...
    def load_runtime(self, runtime_key: str, starting_cash: float) -> PersistedRuntime: ...
    def commit_step(self, runtime_key: str, commit: RuntimeStepCommit) -> CommitOutcome: ...
    def list_trades(self, runtime_key: str | None = None, *, limit: int | None = None) -> tuple[TradeSnapshot, ...]: ...
    def save_runtime_status(self, runtime_key: str, status: HostedRuntimeStatus) -> None: ...
    def load_runtime_status(self, runtime_key: str) -> HostedRuntimeStatus | None: ...
```

- [ ] **Step 1: Write failing runtime-key/enum tests**

```python
from ai_trading.persistence import CommitOutcome, build_runtime_key


def test_build_runtime_key_is_stable() -> None:
    assert build_runtime_key("GC=F", "5m") == "paper:GC=F:5m:online-river:v1"


def test_commit_outcome_exposes_conflict() -> None:
    assert CommitOutcome.COMMITTED.value == "committed"
    assert CommitOutcome.CONFLICT.value == "conflict"
```

- [ ] **Step 2: Verify RED**

```bash
pytest tests/test_persistence_contract.py -q
```

Expected: import failure for `ai_trading.persistence`.

- [ ] **Step 3: Implement `persistence.py` exactly with the interfaces above plus**

```python
def build_runtime_key(symbol: str, interval: str) -> str:
    return f"paper:{symbol}:{interval}:online-river:v1"
```

- [ ] **Step 4: Verify GREEN**

```bash
pytest tests/test_persistence_contract.py -q
```

- [ ] **Step 5: Write failing model-codec tests**

```python
from dataclasses import replace

import pytest

from ai_trading.model_codec import deserialize_model, serialize_model
from ai_trading.online import RiverDirectionModel


def test_model_codec_round_trip() -> None:
    blob = serialize_model(RiverDirectionModel())
    restored = deserialize_model(blob)
    assert blob.format == "joblib-river-v1"
    assert blob.version == 1
    assert len(blob.sha256) == 64
    assert isinstance(restored, RiverDirectionModel)


def test_model_codec_rejects_corrupt_payload() -> None:
    blob = serialize_model(RiverDirectionModel())
    with pytest.raises(ValueError, match="checksum"):
        deserialize_model(replace(blob, payload=blob.payload + b"x"))


def test_model_codec_rejects_unknown_version() -> None:
    blob = serialize_model(RiverDirectionModel())
    with pytest.raises(ValueError, match="format/version"):
        deserialize_model(replace(blob, version=99))
```

- [ ] **Step 6: Verify RED**

```bash
pytest tests/test_model_codec.py -q
```

- [ ] **Step 7: Implement model codec**

```python
from io import BytesIO
import hashlib
import joblib

MODEL_FORMAT = "joblib-river-v1"
MODEL_VERSION = 1


def serialize_model(model: RiverDirectionModel) -> ModelBlob:
    buffer = BytesIO()
    joblib.dump(model, buffer)
    payload = buffer.getvalue()
    return ModelBlob(MODEL_FORMAT, MODEL_VERSION, payload, hashlib.sha256(payload).hexdigest())


def deserialize_model(blob: ModelBlob) -> RiverDirectionModel:
    if blob.format != MODEL_FORMAT or blob.version != MODEL_VERSION:
        raise ValueError("unsupported model format/version")
    if hashlib.sha256(blob.payload).hexdigest() != blob.sha256:
        raise ValueError("model checksum mismatch")
    model = joblib.load(BytesIO(blob.payload))
    if not isinstance(model, RiverDirectionModel):
        raise ValueError("persisted model has unexpected type")
    return model
```

- [ ] **Step 8: Verify GREEN**

```bash
pytest tests/test_model_codec.py -q
```

- [ ] **Step 9: Add reusable audit-record test and helper**

Test:

```python
record = build_audit_record(
    "runtime_step",
    {"processed_bars": 1},
    "GENESIS",
    timestamp_utc="2026-09-15T00:00:00+00:00",
)
assert record["prev_hash"] == "GENESIS"
assert len(record["hash"]) == 64
```

Implement in `audit.py` using the existing canonical hash function; refactor `AuditLog.append` to call it so file behavior is unchanged.

- [ ] **Step 10: Verify audit regressions**

```bash
pytest tests -q -k audit
```

- [ ] **Step 11: Commit Task 1**

```bash
git add src/ai_trading/persistence.py src/ai_trading/model_codec.py src/ai_trading/audit.py tests/test_persistence_contract.py tests/test_model_codec.py tests
git commit -m "feat: define durable persistence contract"
```

---

### Task 2: Backward-compatible file persistence

**Files:**
- Create: `src/ai_trading/file_persistence.py`
- Create: `tests/test_file_persistence.py`

**Interface produced:**

```python
class FilePaperPersistence(PaperPersistence):
    def __init__(
        self,
        *,
        root: str | Path = "artifacts",
        state_store: RuntimeStateStore | None = None,
        trade_journal: TradeJournal | None = None,
        audit_log: AuditLog | None = None,
        status_store: HostedRuntimeStatusStore | None = None,
        model_path: str | Path | None = None,
    ) -> None: ...
```

This constructor explicitly preserves existing test injection such as `state_store=RuntimeStateStore(tmp_path / "state.json")`, `audit_log=AuditLog(...)`, and custom `online_model_path`.

- [ ] **Step 1: Write failing restart-compatibility test**

```python
def test_file_backend_survives_new_instance(tmp_path) -> None:
    backend = FilePaperPersistence(root=tmp_path)
    key = "paper:GC=F:5m:online-river:v1"
    loaded = backend.load_runtime(key, 100_000.0)
    assert loaded.is_new is True
    assert loaded.revision == 0

    outcome = backend.commit_step(
        key,
        RuntimeStepCommit(
            expected_revision=0,
            state=RuntimeState(
                cash=99_900.0,
                units=1.0,
                last_price=100.0,
                peak_equity=100_000.0,
                day_start_equity=100_000.0,
                last_processed="2026-09-15 10:00:00+00:00",
                processed_bars=1,
                last_learning_cycle_bar=0,
            ),
            model=serialize_model(RiverDirectionModel()),
            trade=None,
            audit_event="runtime_step",
            audit_payload={"processed_bars": 1},
        ),
    )
    assert outcome is CommitOutcome.COMMITTED
    restored = FilePaperPersistence(root=tmp_path).load_runtime(key, 100_000.0)
    assert restored.state.cash == 99_900.0
    assert restored.revision == 1
    assert restored.model is not None
```

- [ ] **Step 2: Verify RED**

```bash
pytest tests/test_file_persistence.py -q
```

- [ ] **Step 3: Implement file backend using existing stores**

Defaults:

```python
RuntimeStateStore(root / "runtime_state.json")
TradeJournal(root / "trades.jsonl")
AuditLog(root / "audit.jsonl")
HostedRuntimeStatusStore(root / "runtime_status.json")
model_path = root / "models" / "online-river.joblib"
```

Rules:

- `initialize_schema()` is a no-op.
- `load_runtime()` returns `revision=state.processed_bars`; `is_new` is based on whether the state file existed before loading.
- Existing model bytes are wrapped as `ModelBlob(format="joblib-river-v1", version=1, payload=..., sha256=...)`.
- `commit_step()` returns `CONFLICT` if `expected_revision != current_state.processed_bars`.
- On commit: optional trade append, audit append, state save, atomic model-byte temp-file replace, then `COMMITTED`.
- `list_trades` and runtime-status methods delegate to existing stores.
- The file backend intentionally ignores `runtime_key` because legacy artifacts represent one runtime per directory.

- [ ] **Step 4: Verify file/store regressions**

```bash
pytest tests/test_file_persistence.py tests/test_runtime_state.py tests/test_trade_journal.py tests/test_runtime_status.py -q
```

- [ ] **Step 5: Commit Task 2**

```bash
git add src/ai_trading/file_persistence.py tests/test_file_persistence.py
git commit -m "feat: add file persistence facade"
```

---

### Task 3: PostgreSQL backend, schema, factory, atomicity, and concurrency

**Files:**
- Create: `src/ai_trading/postgres_persistence.py`
- Create: `src/ai_trading/persistence_factory.py`
- Modify: `pyproject.toml`
- Create: `tests/test_postgres_persistence.py`
- Modify: `tests/test_persistence_contract.py`

**Interfaces produced:**

```python
class PostgresPaperPersistence(PaperPersistence):
    def __init__(
        self,
        database_url: str,
        *,
        before_state_commit: Callable[[], None] | None = None,
    ) -> None: ...


def build_persistence_from_env(*, file_root: str | Path = "artifacts") -> PaperPersistence: ...
```

- [ ] **Step 1: Add PostgreSQL dependency**

In `pyproject.toml` dependencies add:

```toml
"psycopg[binary]>=3.2"
```

- [ ] **Step 2: Write failing PostgreSQL schema test**

`tests/test_postgres_persistence.py`:

```python
TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL")
pytestmark = pytest.mark.skipif(not TEST_DATABASE_URL, reason="TEST_DATABASE_URL is not configured")


def test_schema_initialization_is_idempotent() -> None:
    assert TEST_DATABASE_URL is not None
    backend = PostgresPaperPersistence(TEST_DATABASE_URL)
    backend.initialize_schema()
    backend.initialize_schema()
```

Run:

```bash
TEST_DATABASE_URL="postgresql://postgres:postgres@127.0.0.1:5432/ai_trading_test" pytest tests/test_postgres_persistence.py -q
```

Expected: import failure before implementation.

- [ ] **Step 3: Implement exact idempotent schema**

Create these tables from the spec:

- `paper_runtime_state` with `runtime_key` PK, all `RuntimeState` fields, `revision bigint not null default 0`, `updated_at timestamptz`.
- `paper_model_state` with model format/version/`bytea` payload/checksum and FK to runtime state.
- `paper_trades` with deterministic `event_key` and unique `(runtime_key, event_key)`.
- `paper_audit_events` with hash-chain fields and unique `(runtime_key, hash)`.
- `paper_runtime_status` with dedicated engine/symbol/interval/timestamp columns plus `payload jsonb`.

Indexes:

```sql
CREATE INDEX IF NOT EXISTS idx_paper_trades_runtime_id ON paper_trades(runtime_key, id DESC);
CREATE INDEX IF NOT EXISTS idx_paper_audit_runtime_id ON paper_audit_events(runtime_key, id DESC);
```

- [ ] **Step 4: Verify schema GREEN**

Run the Step 2 command again.

- [ ] **Step 5: Add failing persistence/restart tests**

Use a unique runtime key per test. Cover:

```python
loaded = backend.load_runtime(key, 100_000.0)
assert loaded.is_new is True
assert loaded.revision == 0
```

After one commit, construct a second backend and assert state, model checksum, trades, audit effects, revision `1`, and runtime status survive.

- [ ] **Step 6: Implement load/list/status operations**

`load_runtime` must `INSERT ... ON CONFLICT DO NOTHING`, record whether the insert created the row, then select state + revision + optional model.

Trade event key:

```python
canonical = json.dumps(asdict(trade), sort_keys=True, separators=(",", ":"))
event_key = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
```

`list_trades(limit=N)` queries newest first and reverses results before returning so behavior matches `TradeJournal.list`.

`save_runtime_status` uses upsert; `load_runtime_status` reconstructs the dataclass from JSON payload.

- [ ] **Step 7: Add failing atomicity/concurrency tests**

```python
def test_same_revision_has_one_winner(backend) -> None:
    loaded = backend.load_runtime(key, 100_000.0)
    assert backend.commit_step(key, make_commit(loaded.revision)) is CommitOutcome.COMMITTED
    assert backend.commit_step(key, make_commit(loaded.revision)) is CommitOutcome.CONFLICT
    assert backend.load_runtime(key, 100_000.0).revision == 1
```

Add rollback test using `before_state_commit=lambda: (_ for _ in ()).throw(RuntimeError("forced rollback"))`; after the exception, assert revision/trades/model/audit remain unchanged.

- [ ] **Step 8: Implement transaction in this order**

Inside one psycopg transaction:

1. `SELECT revision FROM paper_runtime_state WHERE runtime_key=%s FOR UPDATE`.
2. Missing row => `RuntimeError("runtime state missing")`.
3. Revision mismatch => return `CONFLICT` before any writes.
4. Insert optional trade.
5. Read last audit hash for that runtime, default `GENESIS`; build + insert audit row.
6. Upsert model row.
7. Invoke test-only `before_state_commit` hook when supplied.
8. `UPDATE paper_runtime_state ... SET revision = revision + 1 WHERE runtime_key=%s AND revision=%s`.
9. Require one updated row.
10. Commit via connection context.

Do not catch genuine psycopg errors and do not log the database URL.

- [ ] **Step 9: Write failing factory tests**

```python
def test_factory_uses_file_backend_without_database_url(monkeypatch, tmp_path) -> None:
    monkeypatch.delenv("AI_TRADING_DATABASE_URL", raising=False)
    assert isinstance(build_persistence_from_env(file_root=tmp_path), FilePaperPersistence)
```

For PostgreSQL selection, monkeypatch `PostgresPaperPersistence`, set `AI_TRADING_DATABASE_URL`, and assert constructor receives the URL and `initialize_schema()` is called once. Assert exceptions from initialization propagate.

- [ ] **Step 10: Implement factory**

```python
def build_persistence_from_env(*, file_root: str | Path = "artifacts") -> PaperPersistence:
    database_url = os.getenv("AI_TRADING_DATABASE_URL", "").strip()
    if not database_url:
        return FilePaperPersistence(root=file_root)
    backend = PostgresPaperPersistence(database_url)
    backend.initialize_schema()
    return backend
```

No exception swallowing and no fallback after a PostgreSQL error.

- [ ] **Step 11: Verify Task 3**

```bash
TEST_DATABASE_URL="postgresql://postgres:postgres@127.0.0.1:5432/ai_trading_test" pytest tests/test_postgres_persistence.py tests/test_persistence_contract.py -q
```

- [ ] **Step 12: Commit Task 3**

```bash
git add pyproject.toml src/ai_trading/postgres_persistence.py src/ai_trading/persistence_factory.py tests/test_postgres_persistence.py tests/test_persistence_contract.py
git commit -m "feat: add transactional postgres persistence"
```

---

### Task 4: Refactor `PaperAutonomousRuntime` to one persistence commit

**Files:**
- Modify: `src/ai_trading/runtime.py`
- Create: `tests/test_runtime_persistence.py`
- Modify: `tests/test_runtime.py`

**Interface change:**

```python
PaperAutonomousRuntime(
    ...,
    persistence: PaperPersistence | None = None,
    runtime_key: str | None = None,
)
```

Legacy `state_store`, `audit_log`, `online_model_path`, `trade_journal`, and `lock_path` arguments remain accepted. When `persistence` is absent, runtime constructs `FilePaperPersistence` using those injected legacy objects/paths.

- [ ] **Step 1: Write failing facade-commit test**

Create an in-memory fake persistence returning a known `PersistedRuntime` and recording calls to `commit_step`. Reuse `sample_market()` from `tests/test_runtime.py`. Assert one processed step makes exactly one `RuntimeStepCommit` containing incremented state, serialized model, audit payload, and optional trade.

- [ ] **Step 2: Verify RED**

```bash
pytest tests/test_runtime_persistence.py -q
```

- [ ] **Step 3: Refactor load path**

```python
persisted = self.persistence.load_runtime(self.runtime_key, self.risk_config.starting_cash)
state = persisted.state
if persisted.model is None:
    if not persisted.is_new and state.processed_bars > 0:
        raise ValueError("persisted runtime is missing its online model")
    model = RiverDirectionModel()
else:
    model = deserialize_model(persisted.model)
```

Keep duplicate-bar check before model learning/prediction.

- [ ] **Step 4: Replace four independent writes with one commit**

Build one `RuntimeStepCommit` with current audit payload and call:

```python
outcome = self.persistence.commit_step(self.runtime_key, commit)
```

On `CONFLICT`, return:

```python
RuntimeStepResult(
    processed=False,
    timestamp=execution_time,
    side=0,
    confidence=0.0,
    approved=False,
    reason="persistence revision conflict",
    equity=broker.state.equity,
    units=broker.state.units,
    processed_bars=state.processed_bars,
    retrain_due=False,
)
```

Do not retry or create recovery files in that iteration.

- [ ] **Step 5: Verify runtime behavior**

```bash
pytest tests/test_runtime_persistence.py tests/test_runtime.py tests/test_trade_journal.py -q
```

- [ ] **Step 6: Commit Task 4**

```bash
git add src/ai_trading/runtime.py tests/test_runtime_persistence.py tests/test_runtime.py
git commit -m "refactor: commit paper runtime atomically"
```

---

### Task 5: Durable hosted status and dashboard reads

**Files:**
- Modify: `src/ai_trading/hosted_runtime.py`
- Modify: `src/ai_trading/dashboard.py`
- Create: `tests/test_hosted_persistence.py`
- Modify: `tests/test_hosted_runtime.py`
- Modify: `tests/test_dashboard.py`
- Modify: `tests/test_dashboard_engine_status.py`
- Modify: `tests/test_dashboard_health.py`

- [ ] **Step 1: Write failing hosted wiring tests**

Assert:

```python
HostedPaperSettings(symbol="GC=F", interval="5m").runtime_key == "paper:GC=F:5m:online-river:v1"
```

Use a fake persistence to verify STARTING/RUNNING/ERROR statuses call `save_runtime_status(runtime_key, status)` and runtime receives the same backend/key.

- [ ] **Step 2: Verify RED**

```bash
pytest tests/test_hosted_persistence.py -q
```

- [ ] **Step 3: Implement hosted injection**

Add `runtime_key` property using `build_runtime_key`.

Change signatures:

```python
def run_hosted_paper_loop(settings: HostedPaperSettings, *, persistence: PaperPersistence | None = None) -> None: ...

def start_hosted_paper_runtime(
    *,
    settings: HostedPaperSettings | None = None,
    persistence: PaperPersistence | None = None,
    runner: Callable[..., None] = run_hosted_paper_loop,
) -> Thread | None: ...
```

Build persistence only when not injected. Use it for worker statuses and `PaperAutonomousRuntime`.

- [ ] **Step 4: Write failing dashboard persistence tests**

Fake persistence returns known state/trades/status while local files are empty; assert HTML shows durable values.

Failure fake raises `RuntimeError("storage unavailable")`; assert dashboard does not synthesize `100,000.00`, `/api/status` exposes constant public storage error, and `/healthz` stays HTTP 200 with web healthy / engine unhealthy.

- [ ] **Step 5: Implement dashboard persistence path**

Extend `render_dashboard`:

```python
persistence: PaperPersistence | None = None,
runtime_key: str | None = None,
```

When both are present, read trades/state/status from persistence. Otherwise preserve current direct file-store parameters for compatibility.

In `serve_dashboard`, read hosted settings once, build persistence once, derive runtime key once, and pass the same backend to worker + request handlers.

On read failure, public JSON is:

```json
{"engine_status":"ERROR","engine_healthy":false,"storage_healthy":false,"error":"storage unavailable"}
```

Do not serialize connection strings or exception reprs.

- [ ] **Step 6: Verify hosted/dashboard tests**

```bash
pytest tests/test_hosted_persistence.py tests/test_hosted_runtime.py tests/test_dashboard.py tests/test_dashboard_engine_status.py tests/test_dashboard_health.py -q
```

- [ ] **Step 7: Commit Task 5**

```bash
git add src/ai_trading/hosted_runtime.py src/ai_trading/dashboard.py tests/test_hosted_persistence.py tests/test_hosted_runtime.py tests/test_dashboard.py tests/test_dashboard_engine_status.py tests/test_dashboard_health.py
git commit -m "feat: use durable persistence in hosted dashboard"
```

---

### Task 6: PostgreSQL CI, documentation, and restart proof

**Files:**
- Modify: `.github/workflows/ci.yml`
- Modify: `README.md`

- [ ] **Step 1: Add PostgreSQL 16 service to existing CI job**

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

env:
  TEST_DATABASE_URL: postgresql://postgres:postgres@127.0.0.1:5432/ai_trading_test
```

Keep Python 3.11, Ruff, and `pytest -q`.

- [ ] **Step 2: Run workflow-equivalent verification**

```bash
python -m pip install -e ".[dev]"
ruff check src tests
TEST_DATABASE_URL="postgresql://postgres:postgres@127.0.0.1:5432/ai_trading_test" pytest -q
```

Expected: Ruff exit 0; Pytest 0 failed.

- [ ] **Step 3: Document production env behavior in README**

Document exactly:

```text
AI_TRADING_DATABASE_URL=<PostgreSQL connection string with TLS enabled>
```

State that PostgreSQL is authoritative when configured, invalid DB config fails closed, no variable means local file mode, connection strings are secrets, and live order routing remains absent.

- [ ] **Step 4: Commit CI/docs**

```bash
git add .github/workflows/ci.yml README.md
git commit -m "ci: verify durable postgres persistence"
```

- [ ] **Step 5: Open PR and require real GitHub Actions green before merge**

PR summary:

```text
Adds durable PostgreSQL persistence for paper runtime state, model, trades, audit history, and hosted status. Includes revision-based overlap protection and keeps file-backed local behavior when AI_TRADING_DATABASE_URL is absent. Live trading remains disabled.
```

- [ ] **Step 6: Configure Render only when a real Supabase PostgreSQL URL is available**

Merge the environment variable into the existing Render service:

```text
AI_TRADING_DATABASE_URL=<Supabase PostgreSQL URL with required TLS settings>
```

Never replace unrelated Render environment variables and never write the secret to Git or status output.

- [ ] **Step 7: Prove persistence across restart/redeploy**

Before restart record non-secret baseline: runtime key, processed bars, cash/equity/units, trade count, engine status. After controlled restart verify:

1. processed bars do not reset;
2. cash/units/equity recover before the next new bar;
3. old trades remain visible;
4. model loads without checksum/version error;
5. `last_processed` is not committed twice;
6. runtime status resumes under the same runtime key.

- [ ] **Step 8: Final verification**

```bash
ruff check src tests
TEST_DATABASE_URL="postgresql://postgres:postgres@127.0.0.1:5432/ai_trading_test" pytest -q
```

Then verify merged GitHub Actions green and Render deploy `live` before claiming completion.

---

## Requirement Traceability

- PostgreSQL source of truth: Tasks 3–5.
- Atomic state/model/trade/audit: Task 3.
- Overlapping deploy protection: Task 3 + conflict handling Task 4.
- Dashboard/status recovery: Task 5.
- File fallback compatibility: Task 2.
- Fail-closed DB behavior: Tasks 3–5.
- Checksum/version validation: Task 1.
- PostgreSQL CI coverage: Task 6.
- Restart proof: Task 6.
- Paper-only safety: global constraint; no task adds broker routing.

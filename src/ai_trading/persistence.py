from __future__ import annotations

import json
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Protocol

import joblib

from .burnin import BurnInSnapshot
from .performance_metrics import TradePerformanceMetrics
from .runtime_state import RuntimeState
from .runtime_status import HostedRuntimeStatus
from .trade_journal import TradeSnapshot


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
class SchedulerDelivery:
    timestamp_utc: str
    source: str
    status_code: int
    ok: bool
    processed: int | None = None


@dataclass(frozen=True)
class RuntimeStepCommit:
    expected_revision: int
    state: RuntimeState
    model: ModelBlob
    trade: TradeSnapshot | None
    audit_event: str
    audit_payload: dict[str, Any]
    observed_regime: str | None = None


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

    def load_trade_performance(self, runtime_key: str) -> TradePerformanceMetrics: ...

    def load_portfolio_trade_performance(
        self,
        runtime_keys: tuple[str, ...],
    ) -> TradePerformanceMetrics: ...

    def list_burnin_snapshots(self, runtime_key: str) -> tuple[BurnInSnapshot, ...]: ...

    def list_regimes(self, runtime_key: str) -> tuple[str, ...]: ...

    def save_runtime_status(self, runtime_key: str, status: HostedRuntimeStatus) -> None: ...

    def load_runtime_status(self, runtime_key: str) -> HostedRuntimeStatus | None: ...

    def record_scheduler_delivery(self, delivery: SchedulerDelivery) -> None: ...

    def list_scheduler_deliveries(
        self,
        *,
        limit: int = 20,
    ) -> tuple[SchedulerDelivery, ...]: ...


def build_runtime_key(symbol: str, interval: str) -> str:
    return f"paper:{symbol}:{interval}:online-river:v1"


@dataclass(frozen=True)
class ModelArtifact:
    path: Path
    metadata: dict[str, Any]


class ModelStore:
    def __init__(self, root: str | Path = "artifacts/models") -> None:
        self.root = Path(root)
        self.pointer_path = self.root / "active.json"

    def save(self, name: str, model: object, metadata: dict[str, Any] | None = None) -> ModelArtifact:
        self.root.mkdir(parents=True, exist_ok=True)
        path = self.root / f"{name}.joblib"
        payload = {"model": model, "metadata": metadata or {}}
        joblib.dump(payload, path)
        return ModelArtifact(path=path, metadata=payload["metadata"])

    def load(self, name: str) -> ModelArtifact:
        path = self.root / f"{name}.joblib"
        if not path.exists():
            raise FileNotFoundError(path)
        payload = joblib.load(path)
        return ModelArtifact(path=path, metadata=dict(payload.get("metadata", {})))

    def load_model(self, name: str) -> object:
        path = self.root / f"{name}.joblib"
        if not path.exists():
            raise FileNotFoundError(path)
        payload = joblib.load(path)
        return payload["model"]

    def activate(self, name: str) -> ModelArtifact:
        artifact = self.load(name)
        self.root.mkdir(parents=True, exist_ok=True)
        temp = self.pointer_path.with_suffix(".tmp")
        temp.write_text(json.dumps({"active": name}, sort_keys=True), encoding="utf-8")
        temp.replace(self.pointer_path)
        return artifact

    def active_name(self) -> str | None:
        if not self.pointer_path.exists():
            return None
        payload = json.loads(self.pointer_path.read_text(encoding="utf-8"))
        value = payload.get("active")
        return str(value) if value else None

    def load_active_model(self) -> object:
        name = self.active_name()
        if name is None:
            raise RuntimeError("No active model")
        return self.load_model(name)

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from .audit import AuditLog
from .burnin import BurnInSnapshot, BurnInTracker
from .mtf_shadow_quality import (
    MultiTimeframeShadowQuality,
    compare_mtf_shadow_audit_payloads,
)
from .performance_metrics import TradePerformanceMetrics, calculate_performance_metrics
from .persistence import (
    CommitOutcome,
    ModelBlob,
    PaperPersistence,
    PersistedRuntime,
    RuntimeStepCommit,
    SchedulerDelivery,
    build_runtime_key,
)
from .runtime_state import RuntimeStateStore
from .runtime_status import HostedRuntimeStatus, HostedRuntimeStatusStore
from .shadow_quality import ShadowQualityComparison, compare_shadow_audit_payloads
from .trade_journal import TradeJournal, TradeSnapshot


_LEGACY_RUNTIME_KEY = build_runtime_key("GC=F", "5m")


class FilePaperPersistence(PaperPersistence):
    """File backend with per-runtime isolation and legacy Gold compatibility."""

    def __init__(
        self,
        root: str | Path = "artifacts",
        *,
        state_store: RuntimeStateStore | None = None,
        trade_journal: TradeJournal | None = None,
        audit_log: AuditLog | None = None,
        status_store: HostedRuntimeStatusStore | None = None,
        model_path: str | Path | None = None,
    ) -> None:
        root_path = Path(root)
        self.root_path = root_path
        self.state_store = state_store or RuntimeStateStore(root_path / "runtime_state.json")
        self.trade_journal = trade_journal or TradeJournal(root_path / "trades.jsonl")
        self.audit_log = audit_log or AuditLog(root_path / "audit.jsonl")
        self.status_store = status_store or HostedRuntimeStatusStore(root_path / "runtime_status.json")
        self.burnin_tracker = BurnInTracker(root_path / "burnin.jsonl")
        self.regimes_path = root_path / "regimes.txt"
        self.scheduler_deliveries_path = root_path / "scheduler_deliveries.jsonl"
        self.model_path = Path(model_path) if model_path is not None else root_path / "models" / "online-river.joblib"

    def _runtime_root(self, runtime_key: str) -> Path:
        if runtime_key == _LEGACY_RUNTIME_KEY:
            return self.root_path
        digest = hashlib.sha256(runtime_key.encode("utf-8")).hexdigest()[:16]
        return self.root_path / "runtimes" / digest

    def _state_store_for(self, runtime_key: str) -> RuntimeStateStore:
        if runtime_key == _LEGACY_RUNTIME_KEY:
            return self.state_store
        return RuntimeStateStore(self._runtime_root(runtime_key) / "runtime_state.json")

    def _trade_journal_for(self, runtime_key: str) -> TradeJournal:
        if runtime_key == _LEGACY_RUNTIME_KEY:
            return self.trade_journal
        return TradeJournal(self._runtime_root(runtime_key) / "trades.jsonl")

    def _audit_log_for(self, runtime_key: str) -> AuditLog:
        if runtime_key == _LEGACY_RUNTIME_KEY:
            return self.audit_log
        return AuditLog(self._runtime_root(runtime_key) / "audit.jsonl")

    def _status_store_for(self, runtime_key: str) -> HostedRuntimeStatusStore:
        if runtime_key == _LEGACY_RUNTIME_KEY:
            return self.status_store
        return HostedRuntimeStatusStore(
            self._runtime_root(runtime_key) / "runtime_status.json"
        )

    def _burnin_tracker_for(self, runtime_key: str) -> BurnInTracker:
        if runtime_key == _LEGACY_RUNTIME_KEY:
            return self.burnin_tracker
        return BurnInTracker(self._runtime_root(runtime_key) / "burnin.jsonl")

    def _regimes_path_for(self, runtime_key: str) -> Path:
        if runtime_key == _LEGACY_RUNTIME_KEY:
            return self.regimes_path
        return self._runtime_root(runtime_key) / "regimes.txt"

    def _model_path_for(self, runtime_key: str) -> Path:
        if runtime_key == _LEGACY_RUNTIME_KEY:
            return self.model_path
        return self._runtime_root(runtime_key) / "models" / "online-river.joblib"

    def initialize_schema(self) -> None:
        return None

    def load_runtime(self, runtime_key: str, starting_cash: float) -> PersistedRuntime:
        state_store = self._state_store_for(runtime_key)
        model_path = self._model_path_for(runtime_key)
        is_new = not state_store.path.exists()
        state = state_store.load(starting_cash)
        model: ModelBlob | None = None
        if model_path.exists():
            payload = model_path.read_bytes()
            model = ModelBlob(
                format="joblib-river-v1",
                version=1,
                payload=payload,
                sha256=hashlib.sha256(payload).hexdigest(),
            )
        return PersistedRuntime(
            state=state,
            model=model,
            revision=state.processed_bars,
            is_new=is_new,
        )

    def commit_step(self, runtime_key: str, commit: RuntimeStepCommit) -> CommitOutcome:
        state_store = self._state_store_for(runtime_key)
        trade_journal = self._trade_journal_for(runtime_key)
        audit_log = self._audit_log_for(runtime_key)
        model_path = self._model_path_for(runtime_key)
        burnin_tracker = self._burnin_tracker_for(runtime_key)
        regimes_path = self._regimes_path_for(runtime_key)
        current = state_store.load(commit.state.cash)
        if current.processed_bars != commit.expected_revision:
            return CommitOutcome.CONFLICT

        if commit.trade is not None:
            trade_journal.append(commit.trade)
        audit_log.append(commit.audit_event, commit.audit_payload)
        state_store.save(commit.state)
        model_path.parent.mkdir(parents=True, exist_ok=True)
        temp = model_path.with_suffix(".tmp")
        temp.write_bytes(commit.model.payload)
        temp.replace(model_path)
        state = commit.state
        if commit.observed_regime:
            regimes = set(self.list_regimes(runtime_key))
            regimes.add(commit.observed_regime)
            regimes_path.parent.mkdir(parents=True, exist_ok=True)
            regimes_path.write_text(
                "\n".join(sorted(regimes)) + "\n",
                encoding="utf-8",
            )
        burnin_tracker.append(
            equity=state.cash + state.units * state.last_price,
            regimes_covered=len(self.list_regimes(runtime_key)),
            processed_bars=state.processed_bars,
        )
        return CommitOutcome.COMMITTED

    def list_trades(
        self,
        runtime_key: str | None = None,
        *,
        limit: int | None = None,
    ) -> tuple[TradeSnapshot, ...]:
        if runtime_key is not None:
            return self._trade_journal_for(runtime_key).list(limit=limit)

        trades = list(self.trade_journal.list())
        runtimes_root = self.root_path / "runtimes"
        if runtimes_root.exists():
            for path in sorted(runtimes_root.glob("*/trades.jsonl")):
                trades.extend(TradeJournal(path).list())
        if limit is not None:
            trades = trades[-limit:]
        return tuple(trades)

    def load_trade_performance(self, runtime_key: str) -> TradePerformanceMetrics:
        return calculate_performance_metrics(
            self._trade_journal_for(runtime_key).list()
        )

    def load_portfolio_trade_performance(
        self,
        runtime_keys: tuple[str, ...],
    ) -> TradePerformanceMetrics:
        trades: list[TradeSnapshot] = []
        for runtime_key in runtime_keys:
            trades.extend(self._trade_journal_for(runtime_key).list())
        return calculate_performance_metrics(tuple(trades))

    def list_burnin_snapshots(self, runtime_key: str) -> tuple[BurnInSnapshot, ...]:
        return tuple(self._burnin_tracker_for(runtime_key).read())

    def list_regimes(self, runtime_key: str) -> tuple[str, ...]:
        regimes_path = self._regimes_path_for(runtime_key)
        if not regimes_path.exists():
            return ()
        return tuple(
            line.strip()
            for line in regimes_path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        )

    def load_shadow_quality(self, runtime_key: str) -> ShadowQualityComparison:
        audit_log = self._audit_log_for(runtime_key)
        if not audit_log.path.exists():
            return compare_shadow_audit_payloads(())
        payloads = []
        with audit_log.path.open("r", encoding="utf-8") as handle:
            for line in handle:
                if not line.strip():
                    continue
                try:
                    record = json.loads(line)
                except json.JSONDecodeError:
                    continue
                payload = record.get("payload")
                if isinstance(payload, dict) and "shadow_challenger" in payload:
                    payloads.append(payload)
        return compare_shadow_audit_payloads(payloads)

    def load_mtf_shadow_quality(
        self,
        runtime_key: str,
        *,
        config_name: str | None = None,
    ) -> MultiTimeframeShadowQuality:
        audit_log = self._audit_log_for(runtime_key)
        if not audit_log.path.exists():
            return compare_mtf_shadow_audit_payloads((), config_name=config_name)
        payloads = []
        with audit_log.path.open("r", encoding="utf-8") as handle:
            for line in handle:
                if not line.strip():
                    continue
                try:
                    record = json.loads(line)
                except json.JSONDecodeError:
                    continue
                payload = record.get("payload")
                if isinstance(payload, dict):
                    payloads.append(payload)
        return compare_mtf_shadow_audit_payloads(payloads, config_name=config_name)

    def save_runtime_status(self, runtime_key: str, status: HostedRuntimeStatus) -> None:
        self._status_store_for(runtime_key).save(status)

    def load_runtime_status(self, runtime_key: str) -> HostedRuntimeStatus | None:
        return self._status_store_for(runtime_key).load()


    def record_scheduler_delivery(self, delivery: SchedulerDelivery) -> None:
        self.scheduler_deliveries_path.parent.mkdir(parents=True, exist_ok=True)
        with self.scheduler_deliveries_path.open("a", encoding="utf-8") as handle:
            handle.write(
                json.dumps(
                    {
                        "timestamp_utc": delivery.timestamp_utc,
                        "source": delivery.source,
                        "status_code": delivery.status_code,
                        "ok": delivery.ok,
                        "processed": delivery.processed,
                    },
                    sort_keys=True,
                )
                + "\n"
            )

    def list_scheduler_deliveries(
        self,
        *,
        limit: int = 20,
    ) -> tuple[SchedulerDelivery, ...]:
        if limit <= 0 or not self.scheduler_deliveries_path.exists():
            return ()

        deliveries: list[SchedulerDelivery] = []
        with self.scheduler_deliveries_path.open("r", encoding="utf-8") as handle:
            for line in handle:
                if not line.strip():
                    continue
                try:
                    payload = json.loads(line)
                    deliveries.append(
                        SchedulerDelivery(
                            timestamp_utc=str(payload["timestamp_utc"]),
                            source=str(payload["source"]),
                            status_code=int(payload["status_code"]),
                            ok=bool(payload["ok"]),
                            processed=(
                                None
                                if payload.get("processed") is None
                                else int(payload["processed"])
                            ),
                        )
                    )
                except (KeyError, TypeError, ValueError, json.JSONDecodeError):
                    continue
        return tuple(deliveries[-limit:])

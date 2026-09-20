from __future__ import annotations

import hashlib
import json
from pathlib import Path

from .audit import AuditLog
from .burnin import BurnInSnapshot, BurnInTracker
from .performance_metrics import TradePerformanceMetrics, calculate_performance_metrics
from .persistence import (
    CommitOutcome,
    ModelBlob,
    PaperPersistence,
    PersistedRuntime,
    RuntimeStepCommit,
)
from .runtime_state import RuntimeStateStore
from .mtf_shadow_quality import (
    MultiTimeframeShadowQuality,
    compare_mtf_shadow_audit_payloads,
)
from .runtime_status import HostedRuntimeStatus, HostedRuntimeStatusStore
from .shadow_quality import ShadowQualityComparison, compare_shadow_audit_payloads
from .trade_journal import TradeJournal, TradeSnapshot


class FilePaperPersistence(PaperPersistence):
    """Compatibility backend over the existing local artifact files."""

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
        self.state_store = state_store or RuntimeStateStore(root_path / "runtime_state.json")
        self.trade_journal = trade_journal or TradeJournal(root_path / "trades.jsonl")
        self.audit_log = audit_log or AuditLog(root_path / "audit.jsonl")
        self.status_store = status_store or HostedRuntimeStatusStore(root_path / "runtime_status.json")
        self.burnin_tracker = BurnInTracker(root_path / "burnin.jsonl")
        self.regimes_path = root_path / "regimes.txt"
        self.model_path = Path(model_path) if model_path is not None else root_path / "models" / "online-river.joblib"

    def initialize_schema(self) -> None:
        return None

    def load_runtime(self, runtime_key: str, starting_cash: float) -> PersistedRuntime:
        del runtime_key
        is_new = not self.state_store.path.exists()
        state = self.state_store.load(starting_cash)
        model: ModelBlob | None = None
        if self.model_path.exists():
            payload = self.model_path.read_bytes()
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
        del runtime_key
        current = self.state_store.load(commit.state.cash)
        if current.processed_bars != commit.expected_revision:
            return CommitOutcome.CONFLICT

        if commit.trade is not None:
            self.trade_journal.append(commit.trade)
        self.audit_log.append(commit.audit_event, commit.audit_payload)
        self.state_store.save(commit.state)
        self.model_path.parent.mkdir(parents=True, exist_ok=True)
        temp = self.model_path.with_suffix(".tmp")
        temp.write_bytes(commit.model.payload)
        temp.replace(self.model_path)
        state = commit.state
        if commit.observed_regime:
            regimes = set(self.list_regimes(""))
            regimes.add(commit.observed_regime)
            self.regimes_path.parent.mkdir(parents=True, exist_ok=True)
            self.regimes_path.write_text(
                "\n".join(sorted(regimes)) + "\n",
                encoding="utf-8",
            )
        self.burnin_tracker.append(
            equity=state.cash + state.units * state.last_price,
            regimes_covered=len(self.list_regimes("")),
            processed_bars=state.processed_bars,
        )
        return CommitOutcome.COMMITTED

    def list_trades(
        self,
        runtime_key: str | None = None,
        *,
        limit: int | None = None,
    ) -> tuple[TradeSnapshot, ...]:
        del runtime_key
        return self.trade_journal.list(limit=limit)

    def load_trade_performance(self, runtime_key: str) -> TradePerformanceMetrics:
        del runtime_key
        return calculate_performance_metrics(self.trade_journal.list())

    def list_burnin_snapshots(self, runtime_key: str) -> tuple[BurnInSnapshot, ...]:
        del runtime_key
        return tuple(self.burnin_tracker.read())

    def list_regimes(self, runtime_key: str) -> tuple[str, ...]:
        del runtime_key
        if not self.regimes_path.exists():
            return ()
        return tuple(
            line.strip()
            for line in self.regimes_path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        )

    def load_shadow_quality(self, runtime_key: str) -> ShadowQualityComparison:
        del runtime_key
        if not self.audit_log.path.exists():
            return compare_shadow_audit_payloads(())
        payloads = []
        with self.audit_log.path.open("r", encoding="utf-8") as handle:
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
    ) -> MultiTimeframeShadowQuality:
        del runtime_key
        if not self.audit_log.path.exists():
            return compare_mtf_shadow_audit_payloads(())
        payloads = []
        with self.audit_log.path.open("r", encoding="utf-8") as handle:
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
        return compare_mtf_shadow_audit_payloads(payloads)

    def save_runtime_status(self, runtime_key: str, status: HostedRuntimeStatus) -> None:
        del runtime_key
        self.status_store.save(status)

    def load_runtime_status(self, runtime_key: str) -> HostedRuntimeStatus | None:
        del runtime_key
        return self.status_store.load()

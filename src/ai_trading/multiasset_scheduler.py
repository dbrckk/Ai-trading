from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from time import monotonic, sleep

import pandas as pd

from .audit_chain import verify_audit_chain
from .audit_integrity import verify_jsonl_audit
from .control_plane import read_control_plane
from .multiasset_runtime import MultiAssetPaperRuntime, MultiAssetStepResult
from .recovery import recover_latest_consistent_state
from .session_integrity import compute_session_fingerprint
from .startup_check import run_startup_check
from .state_snapshot import AtomicSnapshotStore
from .watchdog import HeartbeatStore


@dataclass(frozen=True)
class MultiAssetSchedulerConfig:
    poll_seconds: float = 60.0
    max_iterations: int | None = None
    max_consecutive_errors: int = 5
    error_backoff_seconds: float = 5.0
    max_error_backoff_seconds: float = 300.0
    snapshot_every_iterations: int = 1
    verify_audit_every_iterations: int = 1
    recover_after_errors: int = 2
    snapshot_retention: int = 20


class MultiAssetPaperScheduler:
    def __init__(
        self,
        *,
        runtime: MultiAssetPaperRuntime,
        data_loader: Callable[[], dict[str, pd.DataFrame]],
        config: MultiAssetSchedulerConfig | None = None,
        heartbeat_store: HeartbeatStore | None = None,
        snapshot_store: AtomicSnapshotStore | None = None,
    ) -> None:
        self.runtime = runtime
        self.data_loader = data_loader
        self.config = config or MultiAssetSchedulerConfig()
        self.heartbeat_store = heartbeat_store or HeartbeatStore(
            "artifacts/multiasset_heartbeat.json"
        )
        self.snapshot_store = snapshot_store or AtomicSnapshotStore()

    def _state_files(self) -> list:
        return [
            self.runtime.state_store.path,
            self.runtime.crisis_state_store.path,
            self.runtime.governor_state_store.path,
            self.runtime.allocation_state_store.path,
            self.runtime.allocator_config_store.path,
            self.runtime.drift_retrain_store.path,
            self.runtime.champion_probation_store.path,
            self.runtime.model_quarantine_store.path,
            self.runtime.resilience_state_store.path,
        ]

    def _jsonl_files(self) -> list:
        return [
            self.runtime.champion_registry.path,
            self.runtime.lifecycle_log.path,
            self.runtime.readiness_history_store.path,
        ]

    def _active_model_files(self) -> list:
        active = self.runtime.champion_registry.active()
        if active is None:
            return []
        promotions = [
            event
            for event in self.runtime.lifecycle_log.list()
            if event.event == "promotion" and event.version == active.version
        ]
        if not promotions:
            return []
        artifact_path = promotions[-1].artifact_path
        return [artifact_path] if artifact_path else []

    def _snapshot_files(self) -> list:
        return self._state_files() + self._jsonl_files() + self._active_model_files()

    def _audit_error(self, exc: Exception, consecutive_errors: int) -> None:
        self.runtime.audit.append(
            "multiasset_scheduler_error",
            {
                "error": repr(exc),
                "consecutive_errors": consecutive_errors,
            },
        )

    def _verify_audit(self) -> None:
        report = verify_jsonl_audit(self.runtime.audit.path)
        if self.runtime.audit.path.exists() and not report.valid:
            raise RuntimeError(
                f"audit integrity failure at line {report.invalid_line}"
            )

        chain = verify_audit_chain(self.runtime.audit.path)
        if self.runtime.audit.path.exists() and not chain.valid:
            raise RuntimeError(
                f"audit hash-chain failure at line {chain.invalid_line}: {chain.reason}"
            )

    def _snapshot(self) -> None:
        snapshot = self.snapshot_store.create(self._snapshot_files())
        fingerprint = compute_session_fingerprint(
            self._snapshot_files(),
            self.runtime.audit.path,
        )
        self.runtime.audit.append(
            "session_checkpoint",
            {
                "snapshot": str(snapshot),
                "fingerprint": fingerprint.fingerprint,
                "state_hashes": fingerprint.state_hashes,
                "audit_tail_hash": fingerprint.audit_tail_hash,
            },
        )
        self.snapshot_store.prune(self.config.snapshot_retention)

    def run(self) -> list[MultiAssetStepResult]:
        startup = run_startup_check(
            audit_path=self.runtime.audit.path,
            state_files=self._state_files(),
            jsonl_files=self._jsonl_files(),
            snapshot_store=self.snapshot_store,
            governor_store=self.runtime.governor_state_store,
            champion_registry=self.runtime.champion_registry,
            lifecycle_log=self.runtime.lifecycle_log,
            readiness_history_store=self.runtime.readiness_history_store,
        )
        if not startup.ready and startup.snapshot_available:
            recovery = recover_latest_consistent_state(
                self.snapshot_store,
                destination_root="artifacts",
                audit_path=self.runtime.audit.path,
                state_files=self._snapshot_files(),
            )
            self.runtime.audit.append(
                "startup_recovery",
                {
                    "restored": recovery.restored,
                    "snapshot": recovery.snapshot,
                    "reason": recovery.reason,
                    "verified": recovery.verified,
                    "mismatches": list(recovery.mismatches),
                    "candidates_tested": recovery.candidates_tested,
                    "fallback_depth": recovery.fallback_depth,
                    "initial_reasons": list(startup.reasons),
                },
            )
            self.runtime.lifecycle_log.append(
                event=(
                    "recovery_succeeded"
                    if recovery.restored
                    else "recovery_failed"
                ),
                version="",
                model_name="",
                reason=recovery.reason,
                failure_type="" if recovery.restored else "technical_failure",
                metadata={
                    "snapshot": recovery.snapshot,
                    "verified": recovery.verified,
                    "mismatches": list(recovery.mismatches),
                    "candidates_tested": recovery.candidates_tested,
                    "fallback_depth": recovery.fallback_depth,
                    "phase": "startup",
                },
            )
            if recovery.restored:
                startup = run_startup_check(
                    audit_path=self.runtime.audit.path,
                    state_files=self._state_files(),
                    jsonl_files=self._jsonl_files(),
                    snapshot_store=self.snapshot_store,
                    governor_store=self.runtime.governor_state_store,
                    champion_registry=self.runtime.champion_registry,
                    lifecycle_log=self.runtime.lifecycle_log,
                    readiness_history_store=self.runtime.readiness_history_store,
                )

        if not startup.ready:
            raise RuntimeError(
                "multiasset scheduler startup self-check failed: "
                + "; ".join(startup.reasons)
            )

        results: list[MultiAssetStepResult] = []
        iteration = 0
        consecutive_errors = 0

        while self.config.max_iterations is None or iteration < self.config.max_iterations:
            status = read_control_plane(
                governor_store=self.runtime.governor_state_store,
                crisis_store=self.runtime.crisis_state_store,
                lifecycle_log=self.runtime.lifecycle_log,
                resilience_store=self.runtime.resilience_state_store,
            )
            if not status.scheduler_should_run:
                raise RuntimeError(
                    f"multiasset scheduler halted by governor: {status.governor_reason}"
                )

            self.heartbeat_store.write(
                "multiasset_scheduler",
                iteration,
                status="running",
            )
            started = monotonic()

            try:
                if (
                    self.config.verify_audit_every_iterations > 0
                    and iteration % self.config.verify_audit_every_iterations == 0
                ):
                    self._verify_audit()

                markets = self.data_loader()
                result = self.runtime.step(markets)
                results.append(result)
                iteration += 1
                consecutive_errors = 0

                if (
                    self.config.snapshot_every_iterations > 0
                    and iteration % self.config.snapshot_every_iterations == 0
                ):
                    self._snapshot()

                self.heartbeat_store.write(
                    "multiasset_scheduler",
                    iteration,
                    status="ok",
                )
            except Exception as exc:
                consecutive_errors += 1
                self.heartbeat_store.write(
                    "multiasset_scheduler",
                    iteration,
                    status="error",
                )
                self._audit_error(exc, consecutive_errors)

                if (
                    self.config.recover_after_errors > 0
                    and consecutive_errors >= self.config.recover_after_errors
                ):
                    recovery = recover_latest_consistent_state(
                        self.snapshot_store,
                        destination_root="artifacts",
                        audit_path=self.runtime.audit.path,
                        state_files=self._snapshot_files(),
                    )
                    self.runtime.audit.append(
                        "multiasset_recovery",
                        {
                            "restored": recovery.restored,
                            "snapshot": recovery.snapshot,
                            "reason": recovery.reason,
                            "verified": recovery.verified,
                            "mismatches": list(recovery.mismatches),
                            "candidates_tested": recovery.candidates_tested,
                            "fallback_depth": recovery.fallback_depth,
                            "consecutive_errors": consecutive_errors,
                        },
                    )
                    self.runtime.lifecycle_log.append(
                        event=(
                            "recovery_succeeded"
                            if recovery.restored
                            else "recovery_failed"
                        ),
                        version="",
                        model_name="",
                        reason=recovery.reason,
                        failure_type="" if recovery.restored else "technical_failure",
                        metadata={
                            "snapshot": recovery.snapshot,
                            "verified": recovery.verified,
                            "mismatches": list(recovery.mismatches),
                            "candidates_tested": recovery.candidates_tested,
                            "fallback_depth": recovery.fallback_depth,
                            "phase": "runtime",
                            "consecutive_errors": consecutive_errors,
                        },
                    )

                if consecutive_errors >= self.config.max_consecutive_errors:
                    raise RuntimeError(
                        "multiasset scheduler stopped after maximum consecutive errors"
                    ) from exc

                delay = min(
                    self.config.max_error_backoff_seconds,
                    self.config.error_backoff_seconds * (2 ** (consecutive_errors - 1)),
                )
                sleep(max(0.0, delay))
                continue

            if self.config.max_iterations is not None and iteration >= self.config.max_iterations:
                break

            elapsed = monotonic() - started
            sleep(max(0.0, self.config.poll_seconds - elapsed))

        self.heartbeat_store.write(
            "multiasset_scheduler",
            iteration,
            status="stopped",
        )
        return results

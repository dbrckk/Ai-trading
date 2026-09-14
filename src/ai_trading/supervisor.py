from __future__ import annotations

import secrets
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path

from .governor_state_store import GovernorState, GovernorStateStore
from .lifecycle_log import LifecycleEventLog
from .maintenance import MaintenanceStore
from .qualification_guard import validate_qualification_record
from .qualification_store import QualificationStore
from .readiness_handshake import wait_for_worker_readiness
from .reliability import evaluate_reliability
from .resilience import ResilienceStateStore
from .restart_log import RestartLog
from .startup_check import run_startup_check
from .state_snapshot import AtomicSnapshotStore
from .supervisor_lease import SupervisorLeaseStore
from .supervisor_state import SupervisorStateStore
from .watchdog import HeartbeatStore
from .worker_monitor import WorkerMonitorConfig, monitor_worker


@dataclass(frozen=True)
class SupervisorConfig:
    max_restarts: int = 10
    crash_window_seconds: float = 60.0
    max_crashes_in_window: int = 3
    initial_backoff_seconds: float = 2.0
    max_backoff_seconds: float = 60.0
    worker_timeout_seconds: float | None = None
    heartbeat_timeout_seconds: float = 180.0
    heartbeat_startup_grace_seconds: float = 30.0
    readiness_timeout_seconds: float = 30.0
    require_qualification: bool = False
    qualification_symbols: tuple[str, ...] = ()
    qualification_period: str = ""
    qualification_interval: str = ""
    qualification_max_age_hours: float = 24.0
    require_reliability_qualification: bool = False
    min_reliability_score: float = 90.0
    min_normal_ratio: float = 0.90
    max_halt_ratio: float = 0.01
    max_mttr_seconds: float | None = None


@dataclass(frozen=True)
class SupervisorResult:
    restarts: int
    stopped_for_maintenance: bool
    crash_loop_detected: bool
    final_exit_code: int | None


class PaperSupervisor:
    def __init__(
        self,
        *,
        command: list[str],
        state_files: list[str | Path],
        audit_path: str | Path,
        config: SupervisorConfig | None = None,
        lease_store: SupervisorLeaseStore | None = None,
        maintenance_store: MaintenanceStore | None = None,
        restart_log: RestartLog | None = None,
        governor_store: GovernorStateStore | None = None,
        snapshot_store: AtomicSnapshotStore | None = None,
        state_store: SupervisorStateStore | None = None,
        heartbeat_store: HeartbeatStore | None = None,
        qualification_store: QualificationStore | None = None,
        resilience_store: ResilienceStateStore | None = None,
        lifecycle_log: LifecycleEventLog | None = None,
    ) -> None:
        self.command = command
        self.state_files = state_files
        self.audit_path = Path(audit_path)
        self.config = config or SupervisorConfig()
        self.lease_store = lease_store or SupervisorLeaseStore()
        self.maintenance_store = maintenance_store or MaintenanceStore()
        self.restart_log = restart_log or RestartLog()
        self.governor_store = governor_store or GovernorStateStore()
        self.snapshot_store = snapshot_store or AtomicSnapshotStore()
        self.state_store = state_store or SupervisorStateStore()
        self.heartbeat_store = heartbeat_store or HeartbeatStore(
            "artifacts/multiasset_heartbeat.json"
        )
        self.qualification_store = qualification_store or QualificationStore()
        self.resilience_store = resilience_store or ResilienceStateStore()
        self.lifecycle_log = lifecycle_log or LifecycleEventLog()

    def _halt_governor(self, reason: str) -> None:
        previous = self.governor_store.load()
        self.governor_store.save(
            GovernorState(
                verdict="HALT",
                reason=reason,
                consecutive_halts=previous.consecutive_halts + 1,
            )
        )

    def run(self) -> SupervisorResult:
        token = secrets.token_hex(16)
        self.lease_store.acquire(token)
        crashes: list[float] = []
        restarts = 0
        final_exit: int | None = None

        try:
            startup = run_startup_check(
                audit_path=self.audit_path,
                state_files=self.state_files,
                snapshot_store=self.snapshot_store,
                governor_store=self.governor_store,
            )
            if not startup.ready:
                self.state_store.save(
                    status="halted",
                    worker_pid=None,
                    restarts=0,
                    reason="startup self-check failed",
                )
                return SupervisorResult(0, False, False, None)

            if self.config.require_qualification:
                reliability = (
                    evaluate_reliability(
                        self.lifecycle_log,
                        self.resilience_store.load(),
                    )
                    if self.config.require_reliability_qualification
                    else None
                )
                guard = validate_qualification_record(
                    self.qualification_store.load(),
                    symbols=self.config.qualification_symbols,
                    period=self.config.qualification_period,
                    interval=self.config.qualification_interval,
                    max_age_hours=self.config.qualification_max_age_hours,
                    reliability=reliability,
                    min_reliability_score=self.config.min_reliability_score,
                    min_normal_ratio=self.config.min_normal_ratio,
                    max_halt_ratio=self.config.max_halt_ratio,
                    max_mttr_seconds=self.config.max_mttr_seconds,
                )
                if not guard.allowed:
                    reason = "paper qualification gate failed: " + "; ".join(
                        guard.reasons
                    )
                    self._halt_governor(reason)
                    self.state_store.save(
                        status="halted",
                        worker_pid=None,
                        restarts=0,
                        reason=reason,
                    )
                    return SupervisorResult(0, False, False, None)

            while restarts <= self.config.max_restarts:
                resilience = self.resilience_store.load()
                if resilience.mode == "HALT":
                    self.state_store.save(
                        status="halted",
                        worker_pid=None,
                        restarts=restarts,
                        reason="resilience state is HALT",
                    )
                    return SupervisorResult(
                        restarts,
                        False,
                        False,
                        final_exit,
                    )
                if resilience.mode == "COOLDOWN":
                    self.state_store.save(
                        status="maintenance",
                        worker_pid=None,
                        restarts=restarts,
                        reason="resilience cooldown active",
                    )
                    return SupervisorResult(
                        restarts,
                        True,
                        False,
                        final_exit,
                    )

                maintenance = self.maintenance_store.load()
                if maintenance.enabled:
                    self.state_store.save(
                        status="maintenance",
                        worker_pid=None,
                        restarts=restarts,
                        reason=maintenance.reason,
                    )
                    return SupervisorResult(
                        restarts,
                        True,
                        False,
                        final_exit,
                    )

                self.heartbeat_store.path.unlink(missing_ok=True)
                process = subprocess.Popen(self.command)
                self.state_store.save(
                    status="starting",
                    worker_pid=process.pid,
                    restarts=restarts,
                    reason="waiting for worker readiness",
                )

                readiness = wait_for_worker_readiness(
                    self.heartbeat_store,
                    timeout_seconds=self.config.readiness_timeout_seconds,
                    process=process,
                )
                if not readiness.ready:
                    if process.poll() is None:
                        process.terminate()
                        try:
                            process.wait(timeout=5.0)
                        except subprocess.TimeoutExpired:
                            process.kill()
                            process.wait()
                    watch_reason = readiness.reason
                    final_exit = process.returncode
                    runtime = readiness.waited_seconds
                else:
                    self.state_store.save(
                        status="running",
                        worker_pid=process.pid,
                        restarts=restarts,
                        reason="worker ready",
                    )
                    watch = monitor_worker(
                        process,
                        heartbeat_store=self.heartbeat_store,
                        config=WorkerMonitorConfig(
                            max_runtime_seconds=self.config.worker_timeout_seconds,
                            heartbeat_max_age_seconds=self.config.heartbeat_timeout_seconds,
                            startup_grace_seconds=self.config.heartbeat_startup_grace_seconds,
                        ),
                    )
                    watch_reason = watch.reason
                    final_exit = watch.exit_code
                    runtime = watch.runtime_seconds

                if final_exit == 0:
                    self.restart_log.append(
                        exit_code=final_exit,
                        runtime_seconds=runtime,
                        restart_index=restarts,
                        reason="worker exited cleanly",
                    )
                    self.state_store.save(
                        status="stopped",
                        worker_pid=None,
                        restarts=restarts,
                        reason="worker exited cleanly",
                    )
                    return SupervisorResult(
                        restarts,
                        False,
                        False,
                        final_exit,
                    )

                now = time.monotonic()
                crashes = [
                    ts
                    for ts in crashes
                    if now - ts <= self.config.crash_window_seconds
                ]
                crashes.append(now)
                self.restart_log.append(
                    exit_code=final_exit,
                    runtime_seconds=runtime,
                    restart_index=restarts,
                    reason=watch_reason,
                )

                if len(crashes) >= self.config.max_crashes_in_window:
                    self._halt_governor("supervisor crash-loop detected")
                    self.state_store.save(
                        status="halted",
                        worker_pid=None,
                        restarts=restarts,
                        reason="crash-loop detected",
                    )
                    return SupervisorResult(
                        restarts,
                        False,
                        True,
                        final_exit,
                    )

                restarts += 1
                if restarts > self.config.max_restarts:
                    break

                delay = min(
                    self.config.max_backoff_seconds,
                    self.config.initial_backoff_seconds * (2 ** (restarts - 1)),
                )
                self.state_store.save(
                    status="restarting",
                    worker_pid=None,
                    restarts=restarts,
                    reason=f"restart in {delay:.2f}s",
                )
                time.sleep(max(0.0, delay))

            self._halt_governor("supervisor restart budget exhausted")
            self.state_store.save(
                status="halted",
                worker_pid=None,
                restarts=restarts,
                reason="restart budget exhausted",
            )
            return SupervisorResult(restarts, False, False, final_exit)
        finally:
            self.lease_store.release(token)

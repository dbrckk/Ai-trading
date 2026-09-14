from __future__ import annotations

import secrets
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path

from .governor_state_store import GovernorState, GovernorStateStore
from .maintenance import MaintenanceStore
from .restart_log import RestartLog
from .startup_check import run_startup_check
from .state_snapshot import AtomicSnapshotStore
from .supervisor_lease import SupervisorLeaseStore
from .supervisor_state import SupervisorStateStore


@dataclass(frozen=True)
class SupervisorConfig:
    max_restarts: int = 10
    crash_window_seconds: float = 60.0
    max_crashes_in_window: int = 3
    initial_backoff_seconds: float = 2.0
    max_backoff_seconds: float = 60.0


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

            while restarts <= self.config.max_restarts:
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

                started = time.monotonic()
                process = subprocess.Popen(self.command)
                self.state_store.save(
                    status="running",
                    worker_pid=process.pid,
                    restarts=restarts,
                    reason="worker running",
                )
                final_exit = process.wait()
                runtime = time.monotonic() - started

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
                    reason="worker crashed",
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

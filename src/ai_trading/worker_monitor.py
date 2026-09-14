from __future__ import annotations

import subprocess
import time
from dataclasses import dataclass

from .watchdog import HeartbeatStore, WatchdogPolicy, heartbeat_is_stale


@dataclass(frozen=True)
class WorkerMonitorConfig:
    poll_seconds: float = 1.0
    startup_grace_seconds: float = 30.0
    max_runtime_seconds: float | None = None
    heartbeat_max_age_seconds: float = 180.0


@dataclass(frozen=True)
class WorkerMonitorResult:
    exit_code: int | None
    runtime_seconds: float
    reason: str
    forced_stop: bool


def monitor_worker(
    process: subprocess.Popen,
    *,
    heartbeat_store: HeartbeatStore,
    config: WorkerMonitorConfig | None = None,
) -> WorkerMonitorResult:
    config = config or WorkerMonitorConfig()
    started = time.monotonic()

    while True:
        exit_code = process.poll()
        runtime = time.monotonic() - started

        if exit_code is not None:
            return WorkerMonitorResult(
                exit_code=exit_code,
                runtime_seconds=runtime,
                reason="worker exited",
                forced_stop=False,
            )

        if (
            config.max_runtime_seconds is not None
            and runtime >= config.max_runtime_seconds
        ):
            reason = "worker runtime timeout"
            break

        if runtime >= config.startup_grace_seconds:
            heartbeat = heartbeat_store.load()
            if heartbeat_is_stale(
                heartbeat,
                WatchdogPolicy(
                    max_heartbeat_age_seconds=config.heartbeat_max_age_seconds,
                ),
            ):
                reason = "worker heartbeat stale"
                break

        time.sleep(max(0.0, config.poll_seconds))

    process.terminate()
    try:
        process.wait(timeout=5.0)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait()

    return WorkerMonitorResult(
        exit_code=process.returncode,
        runtime_seconds=time.monotonic() - started,
        reason=reason,
        forced_stop=True,
    )

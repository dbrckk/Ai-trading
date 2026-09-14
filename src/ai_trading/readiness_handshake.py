from __future__ import annotations

import subprocess
import time
from dataclasses import dataclass

from .watchdog import HeartbeatStore, WatchdogPolicy, heartbeat_is_stale


@dataclass(frozen=True)
class ReadinessResult:
    ready: bool
    waited_seconds: float
    reason: str


def wait_for_worker_readiness(
    heartbeat_store: HeartbeatStore,
    *,
    timeout_seconds: float = 30.0,
    poll_seconds: float = 0.25,
    max_heartbeat_age_seconds: float = 5.0,
    process: subprocess.Popen | None = None,
) -> ReadinessResult:
    started = time.monotonic()

    while True:
        if process is not None and process.poll() is not None:
            return ReadinessResult(
                ready=False,
                waited_seconds=time.monotonic() - started,
                reason=f"worker exited before readiness with code {process.returncode}",
            )

        heartbeat = heartbeat_store.load()
        if not heartbeat_is_stale(
            heartbeat,
            WatchdogPolicy(
                max_heartbeat_age_seconds=max_heartbeat_age_seconds,
            ),
        ):
            return ReadinessResult(
                ready=True,
                waited_seconds=time.monotonic() - started,
                reason="fresh worker heartbeat observed",
            )

        elapsed = time.monotonic() - started
        if elapsed >= timeout_seconds:
            return ReadinessResult(
                ready=False,
                waited_seconds=elapsed,
                reason="worker readiness heartbeat timeout",
            )

        time.sleep(max(0.0, poll_seconds))

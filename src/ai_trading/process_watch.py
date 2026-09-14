from __future__ import annotations

import subprocess
import time
from dataclasses import dataclass


@dataclass(frozen=True)
class ProcessWatchResult:
    exit_code: int | None
    timed_out: bool
    runtime_seconds: float


def wait_with_timeout(
    process: subprocess.Popen,
    *,
    timeout_seconds: float | None,
) -> ProcessWatchResult:
    started = time.monotonic()
    if timeout_seconds is None:
        exit_code = process.wait()
        return ProcessWatchResult(
            exit_code=exit_code,
            timed_out=False,
            runtime_seconds=time.monotonic() - started,
        )

    try:
        exit_code = process.wait(timeout=timeout_seconds)
        return ProcessWatchResult(
            exit_code=exit_code,
            timed_out=False,
            runtime_seconds=time.monotonic() - started,
        )
    except subprocess.TimeoutExpired:
        process.terminate()
        try:
            process.wait(timeout=5.0)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()
        return ProcessWatchResult(
            exit_code=process.returncode,
            timed_out=True,
            runtime_seconds=time.monotonic() - started,
        )

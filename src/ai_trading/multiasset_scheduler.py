from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from time import monotonic, sleep

import pandas as pd

from .control_plane import read_control_plane
from .multiasset_runtime import MultiAssetPaperRuntime, MultiAssetStepResult


@dataclass(frozen=True)
class MultiAssetSchedulerConfig:
    poll_seconds: float = 60.0
    max_iterations: int | None = None
    max_consecutive_errors: int = 5
    error_backoff_seconds: float = 5.0
    max_error_backoff_seconds: float = 300.0


class MultiAssetPaperScheduler:
    def __init__(
        self,
        *,
        runtime: MultiAssetPaperRuntime,
        data_loader: Callable[[], dict[str, pd.DataFrame]],
        config: MultiAssetSchedulerConfig | None = None,
    ) -> None:
        self.runtime = runtime
        self.data_loader = data_loader
        self.config = config or MultiAssetSchedulerConfig()

    def _audit_error(self, exc: Exception, consecutive_errors: int) -> None:
        self.runtime.audit.append(
            "multiasset_scheduler_error",
            {
                "error": repr(exc),
                "consecutive_errors": consecutive_errors,
            },
        )

    def run(self) -> list[MultiAssetStepResult]:
        results: list[MultiAssetStepResult] = []
        iteration = 0
        consecutive_errors = 0

        while self.config.max_iterations is None or iteration < self.config.max_iterations:
            status = read_control_plane(
                governor_store=self.runtime.governor_state_store,
                crisis_store=self.runtime.crisis_state_store,
            )
            if not status.scheduler_should_run:
                raise RuntimeError(
                    f"multiasset scheduler halted by governor: {status.governor_reason}"
                )

            started = monotonic()
            try:
                markets = self.data_loader()
                result = self.runtime.step(markets)
                results.append(result)
                iteration += 1
                consecutive_errors = 0
            except Exception as exc:
                consecutive_errors += 1
                self._audit_error(exc, consecutive_errors)
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

        return results

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from time import monotonic, sleep

import pandas as pd

from .orchestrator import AutonomousPaperOrchestrator, OrchestrationResult


@dataclass(frozen=True)
class SchedulerConfig:
    poll_seconds: float = 60.0
    max_iterations: int | None = None
    max_consecutive_errors: int = 5
    error_backoff_seconds: float = 5.0
    max_error_backoff_seconds: float = 300.0


class PaperScheduler:
    def __init__(
        self,
        *,
        orchestrator: AutonomousPaperOrchestrator,
        data_loader: Callable[[], pd.DataFrame],
        symbol: str,
        config: SchedulerConfig | None = None,
    ) -> None:
        self.orchestrator = orchestrator
        self.data_loader = data_loader
        self.symbol = symbol
        self.config = config or SchedulerConfig()

    def _audit_error(self, exc: Exception, consecutive_errors: int) -> None:
        runtime = getattr(self.orchestrator, "runtime", None)
        audit = getattr(runtime, "audit", None)
        if audit is not None:
            audit.append(
                "scheduler_error",
                {
                    "symbol": self.symbol,
                    "error": repr(exc),
                    "consecutive_errors": consecutive_errors,
                },
            )

    def run(self) -> list[OrchestrationResult]:
        results: list[OrchestrationResult] = []
        iteration = 0
        consecutive_errors = 0

        while self.config.max_iterations is None or iteration < self.config.max_iterations:
            started = monotonic()
            try:
                df = self.data_loader()
                result = self.orchestrator.step(df, symbol=self.symbol)
                results.append(result)
                iteration += 1
                consecutive_errors = 0
            except Exception as exc:
                consecutive_errors += 1
                self._audit_error(exc, consecutive_errors)
                if consecutive_errors >= self.config.max_consecutive_errors:
                    raise RuntimeError(
                        "scheduler stopped after maximum consecutive errors"
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

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

    def run(self) -> list[OrchestrationResult]:
        results: list[OrchestrationResult] = []
        iteration = 0

        while self.config.max_iterations is None or iteration < self.config.max_iterations:
            started = monotonic()
            df = self.data_loader()
            result = self.orchestrator.step(df, symbol=self.symbol)
            results.append(result)
            iteration += 1

            if self.config.max_iterations is not None and iteration >= self.config.max_iterations:
                break

            elapsed = monotonic() - started
            sleep(max(0.0, self.config.poll_seconds - elapsed))

        return results

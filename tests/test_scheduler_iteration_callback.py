from __future__ import annotations

from types import SimpleNamespace

import pandas as pd

from ai_trading.scheduler import PaperScheduler, SchedulerConfig


class _GovernorStateStore:
    def load(self):
        return SimpleNamespace(verdict="TRADE", consecutive_halts=0)


class _Orchestrator:
    def step(self, df: pd.DataFrame, *, symbol: str):
        return SimpleNamespace(symbol=symbol, rows=len(df))


class _HealthAwareOrchestrator:
    def __init__(self) -> None:
        self.run_health_check: bool | None = None

    def step(
        self,
        df: pd.DataFrame,
        *,
        symbol: str,
        run_health_check: bool = True,
    ):
        self.run_health_check = run_health_check
        return SimpleNamespace(symbol=symbol, rows=len(df))


def test_scheduler_reports_each_completed_iteration() -> None:
    seen: list[object] = []
    scheduler = PaperScheduler(
        orchestrator=_Orchestrator(),
        data_loader=lambda: pd.DataFrame({"Close": [1.0]}),
        symbol="GC=F",
        config=SchedulerConfig(poll_seconds=0.0, max_iterations=1),
        governor_state_store=_GovernorStateStore(),
        on_iteration=seen.append,
    )

    results = scheduler.run()

    assert seen == results
    assert seen[0].symbol == "GC=F"


def test_scheduler_can_skip_expensive_health_check() -> None:
    orchestrator = _HealthAwareOrchestrator()
    scheduler = PaperScheduler(
        orchestrator=orchestrator,
        data_loader=lambda: pd.DataFrame({"Close": [1.0]}),
        symbol="GC=F",
        config=SchedulerConfig(
            poll_seconds=0.0,
            max_iterations=1,
            run_health_check=False,
        ),
        governor_state_store=_GovernorStateStore(),
    )

    scheduler.run()

    assert orchestrator.run_health_check is False

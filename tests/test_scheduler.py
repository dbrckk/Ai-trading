import pandas as pd
import pytest

from ai_trading.scheduler import PaperScheduler, SchedulerConfig


class FakeOrchestrator:
    def __init__(self) -> None:
        self.calls = 0

    def step(self, df: pd.DataFrame, *, symbol: str):
        self.calls += 1
        return {"rows": len(df), "symbol": symbol, "call": self.calls}


def test_scheduler_runs_bounded_iterations_without_sleep() -> None:
    orchestrator = FakeOrchestrator()
    data = pd.DataFrame({"Close": [1.0, 2.0]})
    scheduler = PaperScheduler(
        orchestrator=orchestrator,
        data_loader=lambda: data,
        symbol="GC=F",
        config=SchedulerConfig(poll_seconds=0.0, max_iterations=3),
    )

    results = scheduler.run()
    assert len(results) == 3
    assert orchestrator.calls == 3
    assert results[-1]["call"] == 3


def test_scheduler_recovers_from_transient_loader_error() -> None:
    orchestrator = FakeOrchestrator()
    data = pd.DataFrame({"Close": [1.0, 2.0]})
    attempts = {"count": 0}

    def loader() -> pd.DataFrame:
        attempts["count"] += 1
        if attempts["count"] == 1:
            raise RuntimeError("temporary data failure")
        return data

    scheduler = PaperScheduler(
        orchestrator=orchestrator,
        data_loader=loader,
        symbol="GC=F",
        config=SchedulerConfig(
            poll_seconds=0.0,
            max_iterations=1,
            max_consecutive_errors=3,
            error_backoff_seconds=0.0,
        ),
    )
    results = scheduler.run()
    assert len(results) == 1
    assert attempts["count"] == 2


def test_scheduler_fails_closed_after_repeated_errors() -> None:
    scheduler = PaperScheduler(
        orchestrator=FakeOrchestrator(),
        data_loader=lambda: (_ for _ in ()).throw(RuntimeError("down")),
        symbol="GC=F",
        config=SchedulerConfig(
            poll_seconds=0.0,
            max_iterations=1,
            max_consecutive_errors=2,
            error_backoff_seconds=0.0,
        ),
    )
    with pytest.raises(RuntimeError, match="maximum consecutive errors"):
        scheduler.run()

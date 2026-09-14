import pandas as pd

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

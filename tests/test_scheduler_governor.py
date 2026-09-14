from pathlib import Path

import pandas as pd
import pytest

from ai_trading.governor_state_store import GovernorState, GovernorStateStore
from ai_trading.scheduler import PaperScheduler, SchedulerConfig


class DummyOrchestrator:
    def step(self, df: pd.DataFrame, *, symbol: str):
        return object()


def test_scheduler_stops_after_repeated_governor_halts(tmp_path: Path) -> None:
    store = GovernorStateStore(tmp_path / "governor.json")
    store.save(
        GovernorState(
            verdict="HALT",
            reason="critical data failure",
            consecutive_halts=3,
        )
    )
    scheduler = PaperScheduler(
        orchestrator=DummyOrchestrator(),
        data_loader=lambda: pd.DataFrame({"x": [1]}),
        symbol="TEST",
        config=SchedulerConfig(
            poll_seconds=0.0,
            max_iterations=1,
            max_governor_halts=3,
        ),
        governor_state_store=store,
    )

    with pytest.raises(RuntimeError, match="governor HALT"):
        scheduler.run()

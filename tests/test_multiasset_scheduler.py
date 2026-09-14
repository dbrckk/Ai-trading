from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from ai_trading.crisis_state_store import CrisisStateStore
from ai_trading.governor_state_store import GovernorState, GovernorStateStore
from ai_trading.multiasset_runtime import MultiAssetPaperRuntime
from ai_trading.multiasset_scheduler import (
    MultiAssetPaperScheduler,
    MultiAssetSchedulerConfig,
)


def market(seed: int, n: int = 120) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    idx = pd.date_range("2025-01-01", periods=n, freq="D")
    close = 100.0 * np.cumprod(1.0 + rng.normal(0.0002, 0.01, n))
    return pd.DataFrame(
        {
            "Open": close,
            "High": close * 1.005,
            "Low": close * 0.995,
            "Close": close,
            "Volume": 1000.0,
        },
        index=idx,
    )


def test_multiasset_scheduler_refuses_to_run_when_halted(tmp_path: Path) -> None:
    governor = GovernorStateStore(tmp_path / "governor.json")
    governor.save(GovernorState(verdict="HALT", reason="critical"))
    runtime = MultiAssetPaperRuntime(
        governor_state_store=governor,
        crisis_state_store=CrisisStateStore(tmp_path / "crisis.json"),
        lock_path=str(tmp_path / "runtime.lock"),
    )
    scheduler = MultiAssetPaperScheduler(
        runtime=runtime,
        data_loader=lambda: {"A": market(1), "B": market(2)},
        config=MultiAssetSchedulerConfig(max_iterations=1, poll_seconds=0.0),
    )

    with pytest.raises(RuntimeError, match="halted by governor"):
        scheduler.run()

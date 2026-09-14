import numpy as np
import pandas as pd

from ai_trading.evolution_manager import run_evolution_cycle
from ai_trading.expert_pool import ExpertPoolStore, ExpertRecord


def market(n: int = 360) -> pd.DataFrame:
    idx = pd.date_range("2023-01-01", periods=n, freq="D")
    t = np.arange(n, dtype=float)
    close = 100 + 0.05 * t + 3.0 * np.sin(t / 8.0)
    open_ = close * (1.0 + 0.001 * np.sin(t / 5.0))
    return pd.DataFrame(
        {
            "Open": open_,
            "High": np.maximum(open_, close) * 1.005,
            "Low": np.minimum(open_, close) * 0.995,
            "Close": close,
            "Volume": 1000.0 + t,
        },
        index=idx,
    )


def test_evolution_cycle_mutates_top_parent(tmp_path) -> None:
    store = ExpertPoolStore(tmp_path / "pool.json")
    store.upsert(
        ExpertRecord(
            name="GC=F:trend:h3:t0.001",
            kind="trend",
            status="active",
            score=0.8,
            validation_score=0.8,
            observations=100,
            compute_cost=1.0,
        )
    )
    result = run_evolution_cycle(
        market(),
        symbol="GC=F",
        store=store,
        parent_limit=1,
    )
    assert result.evaluated > 0
    assert len(result.mutated) == result.evaluated

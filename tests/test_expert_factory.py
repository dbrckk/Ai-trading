import numpy as np
import pandas as pd

from ai_trading.expert_factory import FactoryConfig, generate_candidates, run_expert_factory
from ai_trading.expert_pool import ExpertPoolStore


def market(n: int = 260) -> pd.DataFrame:
    idx = pd.date_range("2024-01-01", periods=n, freq="D")
    t = np.arange(n, dtype=float)
    close = 100 + 0.03 * t + 4.0 * np.sin(t / 10.0)
    open_ = close * (1.0 + 0.001 * np.sin(t / 4.0))
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


def test_generate_candidates_respects_cap() -> None:
    candidates = generate_candidates(
        "GC=F",
        FactoryConfig(max_candidates=5),
    )
    assert len(candidates) == 5
    assert len({c.name for c in candidates}) == 5


def test_factory_evaluates_and_persists_candidates(tmp_path) -> None:
    store = ExpertPoolStore(tmp_path / "pool.json")
    result = run_expert_factory(
        market(),
        symbol="GC=F",
        store=store,
        config=FactoryConfig(
            horizons=(1, 3),
            return_thresholds=(0.001,),
            kinds=("trend", "range"),
            max_candidates=4,
            max_promotions_per_run=2,
        ),
    )
    assert result.evaluated > 0
    assert len(store.load()) > 0
    assert result.promoted <= 2

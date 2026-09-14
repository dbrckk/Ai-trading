import numpy as np
import pandas as pd

from ai_trading.expert_pool import ExpertPoolPolicy, ExpertPoolStore
from ai_trading.expert_pool_manager import refresh_expert_pool


def market(n: int = 240) -> pd.DataFrame:
    idx = pd.date_range("2024-01-01", periods=n, freq="D")
    t = np.arange(n, dtype=float)
    close = 100 + 0.04 * t + 3.5 * np.sin(t / 9.0)
    open_ = close * (1.0 + 0.001 * np.sin(t / 4.0))
    return pd.DataFrame(
        {
            "Open": open_,
            "High": np.maximum(open_, close) * 1.005,
            "Low": np.minimum(open_, close) * 0.995,
            "Close": close,
            "Volume": 1200.0 + t,
        },
        index=idx,
    )


def test_refresh_expert_pool_evaluates_all_specialists(tmp_path) -> None:
    store = ExpertPoolStore(tmp_path / "pool.json")
    result = refresh_expert_pool(
        market(),
        symbol="GC=F",
        store=store,
        policy=ExpertPoolPolicy(max_active_experts=2),
    )
    assert set(result.sandbox) == {"trend", "range", "high_vol"}
    assert len(result.records) == 3
    assert sum(r.status == "active" for r in result.records.values()) <= 2

import numpy as np
import pandas as pd

from ai_trading.chaos import ChaosScenario, apply_chaos


def market(n: int = 120) -> pd.DataFrame:
    idx = pd.date_range("2026-01-01", periods=n, freq="D")
    close = 100.0 + np.arange(n, dtype=float)
    return pd.DataFrame(
        {
            "Open": close,
            "High": close + 1.0,
            "Low": close - 1.0,
            "Close": close,
            "Volume": 1000.0,
        },
        index=idx,
    )


def test_chaos_injects_ohlc_violation() -> None:
    markets = {"GC=F": market()}
    out = apply_chaos(
        markets,
        ChaosScenario("ohlc_violation", step=0, symbol="GC=F"),
        current_step=0,
    )
    assert out["GC=F"]["High"].iloc[-1] < out["GC=F"]["Low"].iloc[-1]

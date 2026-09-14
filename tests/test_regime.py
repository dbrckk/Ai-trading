import pandas as pd

from ai_trading.regime import detect_regime


def test_bull_high_vol_regime() -> None:
    row = pd.Series({"trend_10": 0.03, "trend_30": 0.02, "vol_10": 0.03})
    regime = detect_regime(row)
    assert regime.trend == "bull"
    assert regime.volatility == "high_vol"


def test_sideways_normal_vol_regime() -> None:
    row = pd.Series({"trend_10": 0.001, "trend_30": -0.001, "vol_10": 0.01})
    regime = detect_regime(row)
    assert regime.name == "sideways_normal_vol"

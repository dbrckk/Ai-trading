import pandas as pd

from ai_trading.alpha_allocation import AlphaAllocationConfig, alpha_risk_weights


def test_alpha_risk_allocation_prefers_stronger_alpha_per_risk() -> None:
    weights = alpha_risk_weights(
        pd.Series({"A": 0.08, "B": 0.03, "C": -0.02}),
        pd.Series({"A": 0.10, "B": 0.20, "C": 0.10}),
        pd.Series({"A": 0.9, "B": 0.8, "C": 0.7}),
        AlphaAllocationConfig(max_asset_weight=0.6),
    )
    assert weights["A"] > weights["B"]
    assert weights["C"] < 0
    assert sum(abs(v) for v in weights.values) <= 1.0 + 1e-9

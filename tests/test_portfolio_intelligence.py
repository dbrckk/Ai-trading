import numpy as np
import pandas as pd

from ai_trading.portfolio_intelligence import (
    PortfolioIntelligenceConfig,
    apply_portfolio_intelligence,
    estimate_portfolio_volatility,
)


def sample_returns(n: int = 300) -> pd.DataFrame:
    rng = np.random.default_rng(123)
    return pd.DataFrame(
        {
            "A": rng.normal(0.0002, 0.01, n),
            "B": rng.normal(0.0001, 0.015, n),
            "C": rng.normal(0.0003, 0.02, n),
        }
    )


def test_volatility_targeting_scales_weights() -> None:
    returns = sample_returns()
    base = pd.Series({"A": 0.4, "B": 0.3, "C": 0.3})
    weights, report = apply_portfolio_intelligence(
        base,
        returns,
        {"A": 0.9, "B": 0.8, "C": 0.7},
        current_equity=100_000.0,
        peak_equity=100_000.0,
        config=PortfolioIntelligenceConfig(
            target_annual_volatility=0.10,
            max_leverage=1.0,
        ),
    )
    assert 0.0 < sum(abs(v) for v in weights.values) <= 1.0 + 1e-9
    assert report.leverage <= 1.0
    assert estimate_portfolio_volatility(weights, returns) >= 0.0


def test_drawdown_reduces_leverage() -> None:
    returns = sample_returns()
    base = pd.Series({"A": 0.5, "B": 0.5, "C": 0.0})
    _, healthy = apply_portfolio_intelligence(
        base,
        returns,
        {"A": 0.9, "B": 0.9, "C": 0.9},
        current_equity=100_000.0,
        peak_equity=100_000.0,
    )
    _, stressed = apply_portfolio_intelligence(
        base,
        returns,
        {"A": 0.9, "B": 0.9, "C": 0.9},
        current_equity=90_000.0,
        peak_equity=100_000.0,
    )
    assert stressed.leverage <= healthy.leverage
    assert stressed.drawdown_scale < healthy.drawdown_scale


def test_low_confidence_asset_is_zeroed() -> None:
    returns = sample_returns()
    base = pd.Series({"A": 0.5, "B": 0.5, "C": 0.0})
    weights, _ = apply_portfolio_intelligence(
        base,
        returns,
        {"A": 0.9, "B": 0.49, "C": 0.9},
        current_equity=100_000.0,
        peak_equity=100_000.0,
    )
    assert weights["B"] == 0.0

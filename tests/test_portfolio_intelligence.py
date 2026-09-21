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


def test_high_correlation_reduces_leverage() -> None:
    x = np.linspace(-0.02, 0.02, 300)
    returns = pd.DataFrame(
        {
            "A": x,
            "B": x * 1.01,
            "C": np.sin(np.linspace(0, 12, 300)) * 0.005,
        }
    )
    base = pd.Series({"A": 0.5, "B": 0.5, "C": 0.0})

    _, report = apply_portfolio_intelligence(
        base,
        returns,
        {"A": 0.9, "B": 0.9, "C": 0.9},
        current_equity=100_000.0,
        peak_equity=100_000.0,
        config=PortfolioIntelligenceConfig(
            target_annual_volatility=1.0,
            min_leverage=0.10,
            max_leverage=1.0,
            correlation_soft_limit=0.70,
            correlation_hard_limit=0.90,
        ),
    )

    assert report.max_pair_correlation > 0.90
    assert report.correlation_scale == 0.10
    assert report.leverage == 0.10


def test_low_correlation_keeps_full_correlation_scale() -> None:
    returns = sample_returns()
    base = pd.Series({"A": 0.5, "B": 0.5, "C": 0.0})

    _, report = apply_portfolio_intelligence(
        base,
        returns,
        {"A": 0.9, "B": 0.9, "C": 0.9},
        current_equity=100_000.0,
        peak_equity=100_000.0,
    )

    assert report.max_pair_correlation < 0.70
    assert report.correlation_scale == 1.0

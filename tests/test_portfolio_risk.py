import numpy as np
import pandas as pd

from ai_trading.portfolio_risk import PortfolioRiskConfig, evaluate_portfolio_risk


def test_portfolio_risk_rejects_excess_single_asset_exposure() -> None:
    rng = np.random.default_rng(7)
    returns = pd.DataFrame(
        {
            "A": rng.normal(0, 0.01, 200),
            "B": rng.normal(0, 0.01, 200),
        }
    )
    notionals = pd.Series({"A": 60_000.0, "B": 10_000.0})
    report = evaluate_portfolio_risk(
        notionals,
        100_000.0,
        returns,
        PortfolioRiskConfig(max_asset_exposure=0.35),
    )
    assert not report.approved
    assert "single-asset exposure limit exceeded" in report.reasons


def test_portfolio_risk_detects_high_pair_correlation() -> None:
    x = np.linspace(-0.02, 0.02, 200)
    returns = pd.DataFrame({"A": x, "B": x * 1.01})
    notionals = pd.Series({"A": 20_000.0, "B": 20_000.0})
    report = evaluate_portfolio_risk(
        notionals,
        100_000.0,
        returns,
        PortfolioRiskConfig(max_pair_correlation=0.80),
    )
    assert not report.approved
    assert "pair correlation limit exceeded" in report.reasons

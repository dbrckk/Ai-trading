import math

import numpy as np
import pandas as pd
import pytest

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


@pytest.mark.parametrize("equity", [math.nan, math.inf, -math.inf, 0.0])
def test_portfolio_risk_rejects_invalid_equity(equity: float) -> None:
    with pytest.raises(ValueError, match="equity"):
        evaluate_portfolio_risk(
            pd.Series({"A": 10_000.0}),
            equity,
            pd.DataFrame({"A": [0.01, -0.01]}),
        )


@pytest.mark.parametrize("notional", [math.nan, math.inf, -math.inf])
def test_portfolio_risk_rejects_nonfinite_asset_exposure(notional: float) -> None:
    with pytest.raises(ValueError, match="notionals"):
        evaluate_portfolio_risk(
            pd.Series({"A": notional}),
            100_000.0,
            pd.DataFrame({"A": [0.01, -0.01]}),
        )


@pytest.mark.parametrize(
    "field", [
        "max_gross_exposure",
        "max_net_exposure",
        "max_asset_exposure",
        "max_pair_correlation",
    ]
)
def test_portfolio_risk_rejects_nonfinite_limits(field: str) -> None:
    with pytest.raises(ValueError):
        PortfolioRiskConfig(**{field: math.nan})


def test_portfolio_risk_rejects_undefined_correlation_between_active_assets() -> None:
    notionals = pd.Series({"A": 20_000.0, "B": 20_000.0})
    returns = pd.DataFrame({"A": [0.01, -0.01, 0.02], "B": [0.0, 0.0, 0.0]})
    report = evaluate_portfolio_risk(notionals, 100_000.0, returns)
    assert not report.approved
    assert "insufficient pair correlation evidence" in report.reasons


def test_portfolio_risk_rejects_missing_active_asset_history() -> None:
    notionals = pd.Series({"A": 20_000.0, "B": 20_000.0})
    returns = pd.DataFrame({"A": [0.01, -0.01, 0.02]})
    report = evaluate_portfolio_risk(notionals, 100_000.0, returns)
    assert not report.approved
    assert "insufficient pair correlation evidence" in report.reasons


def test_portfolio_risk_ignores_missing_history_for_flat_asset() -> None:
    notionals = pd.Series({"A": 20_000.0, "B": 0.0})
    returns = pd.DataFrame({"A": [0.01, -0.01, 0.02]})
    report = evaluate_portfolio_risk(notionals, 100_000.0, returns)
    assert report.approved
    assert report.max_pair_correlation == 0.0

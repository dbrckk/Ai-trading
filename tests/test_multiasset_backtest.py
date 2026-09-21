import numpy as np
import pandas as pd
import pytest

from ai_trading.config import RiskConfig
from ai_trading.multiasset_backtest import MultiAssetWalkForwardBacktester
from ai_trading.performance import compute_metrics, infer_periods_per_year
from ai_trading.portfolio import AllocationConfig
from ai_trading.portfolio_risk import PortfolioRiskConfig


def market(seed: int, n: int = 420) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    idx = pd.date_range("2022-01-01", periods=n, freq="D")
    rets = rng.normal(0.0002, 0.01, n)
    close = 100.0 * np.cumprod(1.0 + rets)
    open_ = close * (1.0 + rng.normal(0.0, 0.001, n))
    return pd.DataFrame(
        {
            "Open": open_,
            "High": np.maximum(open_, close) * 1.004,
            "Low": np.minimum(open_, close) * 0.996,
            "Close": close,
            "Volume": 1000.0 + np.arange(n),
        },
        index=idx,
    )


def test_multiasset_walk_forward_produces_portfolio_curve() -> None:
    backtester = MultiAssetWalkForwardBacktester(
        risk_config=RiskConfig(min_confidence=0.0),
        allocation_config=AllocationConfig(max_asset_weight=0.6),
        portfolio_risk_config=PortfolioRiskConfig(
            max_gross_exposure=1.0,
            max_net_exposure=1.0,
            max_asset_exposure=0.6,
            max_pair_correlation=0.999,
        ),
        min_train_bars=140,
        test_window_bars=40,
    )
    report = backtester.run(
        {
            "A": market(1),
            "B": market(2),
        }
    )
    assert len(report.equity_curve) > 20
    assert report.decisions > 0
    assert report.trades >= 0
    assert report.metrics.max_drawdown >= 0.0


def test_multiasset_backtest_annualizes_from_actual_timestamps() -> None:
    report = MultiAssetWalkForwardBacktester(
        risk_config=RiskConfig(min_confidence=0.0),
        allocation_config=AllocationConfig(max_asset_weight=0.6),
        portfolio_risk_config=PortfolioRiskConfig(
            max_gross_exposure=1.0,
            max_net_exposure=1.0,
            max_asset_exposure=0.6,
            max_pair_correlation=0.999,
        ),
        min_train_bars=140,
        test_window_bars=40,
    ).run({"A": market(3), "B": market(4)})

    periods = infer_periods_per_year(report.equity_curve.index)
    expected = compute_metrics(report.equity_curve, periods)

    assert report.metrics.sharpe == pytest.approx(expected.sharpe)
    assert report.metrics.annualized_volatility == pytest.approx(
        expected.annualized_volatility
    )

import numpy as np
import pandas as pd
import pytest

from ai_trading.backtest import (
    WalkForwardBacktester,
    WalkForwardConfig,
    _compound_step_returns,
)
from ai_trading.broker import PaperBroker
from ai_trading.config import ModelConfig, RiskConfig
from ai_trading.performance import compute_metrics, infer_periods_per_year


def sample_market(n: int = 360) -> pd.DataFrame:
    idx = pd.date_range("2020-01-01", periods=n, freq="D")
    t = np.arange(n, dtype=float)
    close = 100.0 + 0.04 * t + 4.0 * np.sin(t / 7.0) + 1.5 * np.sin(t / 2.3)
    open_ = close * (1.0 + 0.001 * np.sin(t / 5.0))
    return pd.DataFrame(
        {
            "Open": open_,
            "High": np.maximum(open_, close) * 1.005,
            "Low": np.minimum(open_, close) * 0.995,
            "Close": close,
            "Volume": 1000.0 + 100.0 * np.sin(t / 11.0) + t,
        },
        index=idx,
    )


def test_walk_forward_produces_out_of_sample_report() -> None:
    report = WalkForwardBacktester(
        risk_config=RiskConfig(min_confidence=0.0),
        model_config=ModelConfig(return_threshold=0.001),
        config=WalkForwardConfig(
            min_train_bars=120,
            test_window_bars=40,
            max_train_bars=180,
        ),
    ).run(sample_market())

    assert report.folds >= 2
    assert report.decisions > 0
    assert len(report.equity_curve) == report.decisions
    assert report.equity_curve.index.is_monotonic_increasing
    assert report.metrics.max_drawdown >= 0.0
    assert report.benchmark_metrics.total_return != 0.0


def test_walk_forward_resets_daily_risk_baseline_between_dates(monkeypatch) -> None:
    calls = 0
    original = PaperBroker.reset_day_start

    def tracked_reset(self) -> None:
        nonlocal calls
        calls += 1
        original(self)

    monkeypatch.setattr(PaperBroker, "reset_day_start", tracked_reset)

    report = WalkForwardBacktester(
        risk_config=RiskConfig(min_confidence=0.0),
        model_config=ModelConfig(return_threshold=0.001),
        config=WalkForwardConfig(
            min_train_bars=120,
            test_window_bars=40,
            max_train_bars=180,
        ),
    ).run(sample_market())

    assert report.decisions > 1
    assert calls == report.decisions


def test_regime_step_returns_are_compounded_without_intervening_equity() -> None:
    result = _compound_step_returns([0.10, -0.05, 0.02])
    assert result == pytest.approx((1.10 * 0.95 * 1.02) - 1.0)


def test_walk_forward_annualizes_from_actual_oos_timestamps_by_default() -> None:
    report = WalkForwardBacktester(
        risk_config=RiskConfig(min_confidence=0.0),
        model_config=ModelConfig(return_threshold=0.001),
        config=WalkForwardConfig(
            min_train_bars=120,
            test_window_bars=40,
            max_train_bars=180,
        ),
    ).run(sample_market())

    periods = infer_periods_per_year(report.equity_curve.index)
    expected = compute_metrics(report.equity_curve, periods)

    assert report.metrics.annualized_return == pytest.approx(expected.annualized_return)
    assert report.metrics.annualized_volatility == pytest.approx(
        expected.annualized_volatility
    )

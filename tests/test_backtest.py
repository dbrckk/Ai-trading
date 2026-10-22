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
from ai_trading.risk import RiskDecision, RiskEngine


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


def test_walk_forward_exits_position_after_hard_risk_stop(monkeypatch) -> None:
    """Backtest must account for a stop exit and its turnover/costs."""
    decisions = 0

    def configured_risk(self, prediction, portfolio):
        nonlocal decisions
        decisions += 1
        if decisions == 1:
            return RiskDecision(True, 1, 10_000.0, "approved")
        return RiskDecision(
            False, 0, 0.0, "daily loss limit reached", liquidate_existing=True
        )

    monkeypatch.setattr(RiskEngine, "evaluate", configured_risk)
    rebalances: list[tuple[int, float]] = []
    original_rebalance = PaperBroker.rebalance

    def tracked_rebalance(self, side, target_notional, price):
        rebalances.append((side, target_notional))
        return original_rebalance(self, side, target_notional, price)

    monkeypatch.setattr(PaperBroker, "rebalance", tracked_rebalance)
    report = WalkForwardBacktester(
        risk_config=RiskConfig(min_confidence=0.0),
        model_config=ModelConfig(),
        config=WalkForwardConfig(min_train_bars=120, test_window_bars=40),
    ).run(sample_market())

    assert report.decisions == decisions
    assert report.trades == 2
    assert report.rejected_decisions == decisions - 1
    assert rebalances == [(1, 10_000.0), (0, 0.0)]


def test_turnover_study_selects_on_validation_without_holdout_cherry_picking(
    monkeypatch,
) -> None:
    from types import SimpleNamespace

    from ai_trading.turnover_study import compare_rebalance_thresholds

    endpoints = {
        0.0: (106.0, 108.0),
        0.001: (109.0, 107.0),  # Best validation, bad later holdout
        0.005: (108.0, 116.0),  # Worse validation, attractive holdout
    }

    def fake_backtest(self, market):
        first_end, last_end = endpoints[self.risk_config.min_rebalance_fraction]
        equity = pd.Series(
            np.r_[
                np.linspace(100.0, first_end, 300),
                np.linspace(first_end, last_end, 200),
            ],
            index=market.index,
        )
        return SimpleNamespace(equity_curve=equity, trades=45, folds=5)

    monkeypatch.setattr(WalkForwardBacktester, "run", fake_backtest)
    result = compare_rebalance_thresholds(
        "GC=F",
        sample_market(500),
        thresholds=(0.0, 0.001, 0.005),
    )

    assert result["sample_sufficient"] is True
    assert result["validation_selected_threshold"] == 0.001
    assert result["holdout_passed"] is False
    assert result["review_only"] is True
    assert result["auto_enable"] is False
    assert result["trials"][0]["full_net_return"] == pytest.approx(0.08)


def test_turnover_study_marks_profitable_untouched_holdout_for_review(
    monkeypatch,
) -> None:
    from types import SimpleNamespace

    from ai_trading.turnover_study import compare_rebalance_thresholds

    def fake_backtest(self, market):
        better = self.risk_config.min_rebalance_fraction > 0.0
        first_end = 109.0 if better else 106.0
        last_end = 118.0 if better else 108.0
        equity = pd.Series(
            np.r_[
                np.linspace(100.0, first_end, 300),
                np.linspace(first_end, last_end, 200),
            ],
            index=market.index,
        )
        return SimpleNamespace(equity_curve=equity, trades=45, folds=5)

    monkeypatch.setattr(WalkForwardBacktester, "run", fake_backtest)
    result = compare_rebalance_thresholds(
        "BTC-USD",
        sample_market(500),
        thresholds=(0.0, 0.001),
    )

    assert result["validation_selected_threshold"] == 0.001
    assert result["holdout_passed"] is True
    assert result["auto_enable"] is False


def test_turnover_study_rejects_small_out_of_sample_history(monkeypatch) -> None:
    from types import SimpleNamespace

    from ai_trading.turnover_study import compare_rebalance_thresholds

    def fake_backtest(self, market):
        better = self.risk_config.min_rebalance_fraction > 0.0
        equity = pd.Series(
            np.linspace(100.0, 120.0 if better else 110.0, len(market)),
            index=market.index,
        )
        return SimpleNamespace(equity_curve=equity, trades=45, folds=5)

    monkeypatch.setattr(WalkForwardBacktester, "run", fake_backtest)
    result = compare_rebalance_thresholds(
        "^GDAXI",
        sample_market(120),
        thresholds=(0.0, 0.001),
    )

    assert result["sample_sufficient"] is False
    assert result["validation_selected_threshold"] is None
    assert result["holdout_passed"] is False


def test_turnover_study_reports_zero_cost_counterfactual_without_promoting(
    monkeypatch,
) -> None:
    from types import SimpleNamespace

    from ai_trading.turnover_study import compare_rebalance_thresholds

    calls: list[tuple[float, float, float]] = []

    def fake_backtest(self, market):
        config = self.risk_config
        calls.append((
            config.min_rebalance_fraction,
            config.transaction_cost_bps,
            config.slippage_bps,
        ))
        endpoint = (
            112.0
            if config.transaction_cost_bps == 0 and config.slippage_bps == 0
            else 98.0
        )
        equity = pd.Series(
            np.linspace(100.0, endpoint, len(market)),
            index=market.index,
        )
        return SimpleNamespace(equity_curve=equity, trades=45, folds=5)

    monkeypatch.setattr(WalkForwardBacktester, "run", fake_backtest)
    study = compare_rebalance_thresholds(
        "GC=F",
        sample_market(500),
        thresholds=(0.0, 0.005),
    )

    diagnostic = study["baseline_cost_sensitivity"]
    assert diagnostic["classification"] == "positive_zero_cost_counterfactual_only"
    assert diagnostic["zero_cost_full_return"] == pytest.approx(0.12)
    assert study["trials"][0]["full_net_return"] == pytest.approx(-0.02)
    assert diagnostic["modeled_full_return_gap"] == pytest.approx(0.14)
    assert diagnostic["exact_paid_fees"] is False
    assert calls == [(0.0, 2.0, 1.0), (0.005, 2.0, 1.0), (0.0, 0.0, 0.0)]
    assert study["auto_enable"] is False


def test_turnover_study_does_not_repeat_frictionless_backtest(monkeypatch) -> None:
    from types import SimpleNamespace

    from ai_trading.turnover_study import compare_rebalance_thresholds

    calls = 0

    def fake_backtest(self, market):
        nonlocal calls
        calls += 1
        equity = pd.Series(
            np.linspace(100.0, 99.0, len(market)),
            index=market.index,
        )
        return SimpleNamespace(equity_curve=equity, trades=45, folds=5)

    monkeypatch.setattr(WalkForwardBacktester, "run", fake_backtest)
    study = compare_rebalance_thresholds(
        "BTC-USD",
        sample_market(500),
        risk_config=RiskConfig(transaction_cost_bps=0.0, slippage_bps=0.0),
        thresholds=(0.0, 0.001),
    )

    assert calls == 2
    diagnostic = study["baseline_cost_sensitivity"]
    assert diagnostic["classification"] == "nonpositive_even_without_modeled_costs"
    assert diagnostic["modeled_full_return_gap"] == pytest.approx(0.0)
    assert diagnostic["modeled_holdout_return_gap"] == pytest.approx(0.0)

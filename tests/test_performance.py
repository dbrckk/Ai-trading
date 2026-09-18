import numpy as np
import pandas as pd

from ai_trading.performance import buy_and_hold_equity, compute_metrics, infer_periods_per_year


def test_metrics_for_monotonic_equity() -> None:
    equity = pd.Series(np.linspace(100_000.0, 120_000.0, 253))
    metrics = compute_metrics(equity)
    assert metrics.total_return == pytest.approx(0.20)
    assert metrics.max_drawdown == pytest.approx(0.0)
    assert metrics.annualized_return > 0


def test_buy_and_hold_is_normalized_to_starting_equity() -> None:
    prices = pd.Series([100.0, 110.0, 120.0])
    curve = buy_and_hold_equity(prices, 100_000.0)
    assert curve.iloc[0] == 100_000.0
    assert curve.iloc[-1] == 120_000.0


import pytest


def test_infer_periods_per_year_from_elapsed_timestamps() -> None:
    index = pd.date_range("2026-01-01", periods=13, freq="30D", tz="UTC")
    periods = infer_periods_per_year(index)
    assert periods == pytest.approx(12.175, rel=0.02)

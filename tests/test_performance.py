import numpy as np
import pandas as pd

from ai_trading.performance import buy_and_hold_equity, compute_metrics


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

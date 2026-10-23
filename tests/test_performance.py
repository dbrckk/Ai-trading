import numpy as np
import pandas as pd
import pytest

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



def test_infer_periods_per_year_from_elapsed_timestamps() -> None:
    index = pd.date_range("2026-01-01", periods=13, freq="30D", tz="UTC")
    periods = infer_periods_per_year(index)
    assert periods == pytest.approx(12.175, rel=0.02)

    # Incomplete or reordered histories must not silently inflate Sharpe
    # ratios or transform numeric bar positions into artificial timestamps.
    invalid_timelines = (
        pd.Index([0, 1, 2]),
        pd.Index(["2026-01-01", "invalid", "2026-01-03"]),
        pd.DatetimeIndex(["2026-01-01", "2026-01-01"]),
        pd.DatetimeIndex(["2026-01-02", "2026-01-01"]),
    )
    for invalid_index in invalid_timelines:
        with pytest.raises(ValueError, match="[Tt]imestamps"):
            infer_periods_per_year(invalid_index)


def test_extreme_short_window_annualization_stays_finite() -> None:
    equity = pd.Series([1.0, 1e100])
    metrics = compute_metrics(equity, periods_per_year=525_600.0)
    assert np.isfinite(metrics.annualized_return)


@pytest.mark.parametrize(
    "equity",
    [
        [100.0, np.nan, 110.0],
        [100.0, np.inf, 110.0],
        [100.0, -np.inf, 110.0],
        [100.0, 0.0, 110.0],
        [100.0, -10.0, 110.0],
    ],
)
def test_performance_refuses_incomplete_or_invalid_equity_curves(equity) -> None:
    with pytest.raises(ValueError, match="Equity observations"):
        compute_metrics(pd.Series(equity))


def test_performance_rejects_nonfinite_returns_from_finite_equity() -> None:
    with pytest.raises(ValueError, match="Equity returns"):
        compute_metrics(pd.Series([1e-300, 1e300]))


@pytest.mark.parametrize(
    "prices",
    [
        [100.0, np.nan, 110.0],
        [100.0, np.inf, 110.0],
        [100.0, 0.0, 110.0],
        [100.0, -20.0, 110.0],
    ],
)
def test_benchmark_refuses_invalid_price_history(prices) -> None:
    with pytest.raises(ValueError, match="finite positive benchmark prices"):
        buy_and_hold_equity(pd.Series(prices), 100_000.0)


@pytest.mark.parametrize("capital", [np.nan, np.inf, 0.0, -1.0])
def test_benchmark_refuses_invalid_starting_equity(capital) -> None:
    with pytest.raises(ValueError, match="Benchmark starting equity"):
        buy_and_hold_equity(pd.Series([100.0, 110.0]), capital)

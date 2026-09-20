from __future__ import annotations

import numpy as np
import pandas as pd

from ai_trading.multi_timeframe_features import (
    MTF_CHALLENGER_FEATURES,
    adaptive_return_threshold,
    make_multi_timeframe_challenger_features,
    make_volatility_adaptive_labels,
)


def sample_market(n: int = 2600) -> pd.DataFrame:
    idx = pd.date_range("2026-01-01", periods=n, freq="5min")
    t = np.arange(n, dtype=float)
    close = 100.0 + 0.01 * t + 1.8 * np.sin(t / 19.0)
    open_ = close * (1.0 + 0.0003 * np.sin(t / 7.0))
    return pd.DataFrame(
        {
            "Open": open_,
            "High": np.maximum(open_, close) * 1.002,
            "Low": np.minimum(open_, close) * 0.998,
            "Close": close,
            "Volume": 1000.0 + (t % 50) * 5.0,
        },
        index=idx,
    )


def test_multi_timeframe_features_include_true_contexts() -> None:
    features = make_multi_timeframe_challenger_features(sample_market())

    assert list(features.columns) == MTF_CHALLENGER_FEATURES
    assert features.dropna().shape[0] > 500
    assert {
        "mtf_15m_ret_1",
        "mtf_1h_trend_8",
        "mtf_4h_rsi_6",
    }.issubset(features.columns)


def test_multi_timeframe_features_do_not_change_when_future_prices_change() -> None:
    market = sample_market()
    probe_time = market.index[1800]
    before = make_multi_timeframe_challenger_features(market).loc[probe_time]

    altered = market.copy()
    future = altered.index > probe_time
    altered.loc[future, ["Open", "High", "Low", "Close"]] *= 5.0
    altered.loc[future, "Volume"] *= 10.0
    after = make_multi_timeframe_challenger_features(altered).loc[probe_time]

    pd.testing.assert_series_equal(before, after)


def test_adaptive_labels_use_15_minute_horizon_and_valid_classes() -> None:
    market = sample_market()
    labels = make_volatility_adaptive_labels(
        market,
        horizon_bars=3,
        minimum_threshold=0.001,
        atr_multiplier=0.25,
    )
    threshold = adaptive_return_threshold(
        market,
        minimum_threshold=0.001,
        atr_multiplier=0.25,
    )

    assert set(labels.dropna().astype(int).unique()).issubset({-1, 0, 1})
    assert threshold.dropna().ge(0.001).all()
    assert labels.iloc[-3:].isna().all()

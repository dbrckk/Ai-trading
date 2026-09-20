from __future__ import annotations

import numpy as np
import pandas as pd

from .features import CHALLENGER_FEATURES, make_challenger_features

MTF_CONTEXT_FEATURES = [
    "mtf_15m_ret_1",
    "mtf_15m_ret_4",
    "mtf_15m_trend_8",
    "mtf_15m_vol_8",
    "mtf_15m_rsi_8",
    "mtf_1h_ret_1",
    "mtf_1h_ret_4",
    "mtf_1h_trend_8",
    "mtf_1h_vol_8",
    "mtf_1h_rsi_8",
    "mtf_4h_ret_1",
    "mtf_4h_ret_3",
    "mtf_4h_trend_6",
    "mtf_4h_vol_6",
    "mtf_4h_rsi_6",
]

MTF_CHALLENGER_FEATURES = [*CHALLENGER_FEATURES, *MTF_CONTEXT_FEATURES]


def _infer_base_delta(index: pd.DatetimeIndex) -> pd.Timedelta:
    deltas = index.to_series().diff().dropna()
    deltas = deltas[deltas > pd.Timedelta(0)]
    if deltas.empty:
        raise ValueError("market index does not contain a usable cadence")
    return pd.Timedelta(deltas.median())


def _resample_ohlcv(market: pd.DataFrame, rule: str) -> pd.DataFrame:
    aggregated = market.resample(
        rule,
        closed="left",
        label="right",
    ).agg(
        {
            "Open": "first",
            "High": "max",
            "Low": "min",
            "Close": "last",
            "Volume": "sum",
        }
    )
    return aggregated.dropna(subset=["Open", "High", "Low", "Close"]).copy()


def _rsi(close: pd.Series, window: int) -> pd.Series:
    delta = close.diff()
    average_gain = delta.clip(lower=0.0).rolling(window).mean()
    average_loss = (-delta.clip(upper=0.0)).rolling(window).mean()
    relative_strength = average_gain / average_loss.replace(0.0, np.nan)
    rsi = 100.0 - (100.0 / (1.0 + relative_strength))
    rsi = rsi.mask((average_loss == 0.0) & (average_gain > 0.0), 100.0)
    rsi = rsi.mask((average_loss == 0.0) & (average_gain == 0.0), 50.0)
    return rsi / 100.0


def _context_features(
    frame: pd.DataFrame,
    *,
    prefix: str,
    return_window: int,
    trend_window: int,
    volatility_window: int,
    rsi_window: int,
) -> pd.DataFrame:
    close = frame["Close"].astype(float)
    returns = close.pct_change()
    out = pd.DataFrame(index=frame.index)
    out[f"{prefix}_ret_1"] = returns
    out[f"{prefix}_ret_{return_window}"] = close.pct_change(return_window)
    out[f"{prefix}_trend_{trend_window}"] = (
        close / close.rolling(trend_window).mean() - 1.0
    )
    out[f"{prefix}_vol_{volatility_window}"] = returns.rolling(
        volatility_window
    ).std()
    out[f"{prefix}_rsi_{rsi_window}"] = _rsi(close, rsi_window)
    return out.replace([np.inf, -np.inf], np.nan)


def _align_completed_context(
    market_index: pd.DatetimeIndex,
    context: pd.DataFrame,
    base_delta: pd.Timedelta,
) -> pd.DataFrame:
    availability = market_index + base_delta
    aligned = context.reindex(availability, method="ffill")
    aligned.index = market_index
    return aligned


def make_multi_timeframe_challenger_features(
    market: pd.DataFrame,
) -> pd.DataFrame:
    """Build leakage-safe 5m/15m/1h/4h features on the base market index.

    Higher-timeframe bars are labeled at their close and are only exposed to a
    5-minute signal row once that higher-timeframe close is available at the
    following execution boundary.
    """

    if not isinstance(market.index, pd.DatetimeIndex):
        raise ValueError("multi-timeframe features require a DatetimeIndex")
    if not market.index.is_monotonic_increasing:
        raise ValueError("market index must be sorted")
    if market.index.has_duplicates:
        raise ValueError("market index must be unique")

    required = {"Open", "High", "Low", "Close", "Volume"}
    missing = required.difference(market.columns)
    if missing:
        raise ValueError(f"missing market columns: {sorted(missing)}")

    base = make_challenger_features(market).copy()
    base_delta = _infer_base_delta(market.index)

    contexts = (
        (
            "15min",
            dict(
                prefix="mtf_15m",
                return_window=4,
                trend_window=8,
                volatility_window=8,
                rsi_window=8,
            ),
        ),
        (
            "1h",
            dict(
                prefix="mtf_1h",
                return_window=4,
                trend_window=8,
                volatility_window=8,
                rsi_window=8,
            ),
        ),
        (
            "4h",
            dict(
                prefix="mtf_4h",
                return_window=3,
                trend_window=6,
                volatility_window=6,
                rsi_window=6,
            ),
        ),
    )

    for rule, settings in contexts:
        resampled = _resample_ohlcv(market, rule)
        context = _context_features(resampled, **settings)
        aligned = _align_completed_context(market.index, context, base_delta)
        for column in aligned.columns:
            base[column] = aligned[column]

    return base.loc[:, MTF_CHALLENGER_FEATURES].replace(
        [np.inf, -np.inf],
        np.nan,
    )


def adaptive_return_threshold(
    market: pd.DataFrame,
    *,
    minimum_threshold: float = 0.001,
    atr_multiplier: float = 0.25,
    atr_window: int = 14,
) -> pd.Series:
    if minimum_threshold <= 0:
        raise ValueError("minimum_threshold must be positive")
    if atr_multiplier <= 0:
        raise ValueError("atr_multiplier must be positive")
    if atr_window < 2:
        raise ValueError("atr_window must be at least 2")

    high = market["High"].astype(float)
    low = market["Low"].astype(float)
    close = market["Close"].astype(float)
    previous_close = close.shift(1)
    true_range = pd.concat(
        [
            high - low,
            (high - previous_close).abs(),
            (low - previous_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    atr_pct = true_range.rolling(atr_window).mean() / close.replace(0.0, np.nan)
    return (atr_pct * atr_multiplier).clip(lower=minimum_threshold)


def make_volatility_adaptive_labels(
    market: pd.DataFrame,
    *,
    horizon_bars: int = 3,
    minimum_threshold: float = 0.001,
    atr_multiplier: float = 0.25,
    atr_window: int = 14,
) -> pd.Series:
    """Label 15-minute direction on 5-minute data using a volatility floor."""

    if horizon_bars < 1:
        raise ValueError("horizon_bars must be at least 1")

    close = market["Close"].astype(float)
    future_return = close.shift(-horizon_bars) / close - 1.0
    threshold = adaptive_return_threshold(
        market,
        minimum_threshold=minimum_threshold,
        atr_multiplier=atr_multiplier,
        atr_window=atr_window,
    )

    labels = pd.Series(0, index=market.index, dtype="int8")
    labels.loc[future_return > threshold] = 1
    labels.loc[future_return < -threshold] = -1
    invalid = future_return.isna() | threshold.isna()
    labels.loc[invalid] = pd.NA
    return labels.astype("Int8")

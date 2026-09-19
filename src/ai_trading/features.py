from __future__ import annotations

import numpy as np
import pandas as pd

FEATURES = [
    "ret_1",
    "ret_5",
    "vol_10",
    "trend_10",
    "trend_30",
    "range_pct",
    "volume_z20",
]

CHALLENGER_FEATURES = [
    *FEATURES,
    "ret_15",
    "vol_30",
    "atr_pct_14",
    "rsi_14",
    "range_pos_20",
    "body_pct",
    "volume_ratio_5_20",
]


def make_features(df: pd.DataFrame) -> pd.DataFrame:
    close = df["Close"].astype(float)
    high = df["High"].astype(float)
    low = df["Low"].astype(float)
    volume = df["Volume"].astype(float)

    out = pd.DataFrame(index=df.index)
    out["ret_1"] = close.pct_change()
    out["ret_5"] = close.pct_change(5)
    out["vol_10"] = close.pct_change().rolling(10).std()
    out["trend_10"] = close / close.rolling(10).mean() - 1.0
    out["trend_30"] = close / close.rolling(30).mean() - 1.0
    out["range_pct"] = (high - low) / close.replace(0, np.nan)
    vol_mean = volume.rolling(20).mean()
    raw_vol_std = volume.rolling(20).std()
    vol_std = raw_vol_std.replace(0, np.nan)
    volume_z20 = (volume - vol_mean) / vol_std
    out["volume_z20"] = volume_z20.mask(
        vol_mean.notna() & raw_vol_std.eq(0.0),
        0.0,
    )

    return out.replace([np.inf, -np.inf], np.nan)


def make_challenger_features(df: pd.DataFrame) -> pd.DataFrame:
    """Build richer research features without changing the production feature set."""

    out = make_features(df).copy()
    open_ = df["Open"].astype(float)
    high = df["High"].astype(float)
    low = df["Low"].astype(float)
    close = df["Close"].astype(float)
    volume = df["Volume"].astype(float)

    returns = close.pct_change()
    out["ret_15"] = close.pct_change(15)
    out["vol_30"] = returns.rolling(30).std()

    previous_close = close.shift(1)
    true_range = pd.concat(
        [
            high - low,
            (high - previous_close).abs(),
            (low - previous_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    out["atr_pct_14"] = true_range.rolling(14).mean() / close.replace(0, np.nan)

    delta = close.diff()
    average_gain = delta.clip(lower=0.0).rolling(14).mean()
    average_loss = (-delta.clip(upper=0.0)).rolling(14).mean()
    relative_strength = average_gain / average_loss.replace(0.0, np.nan)
    rsi = 100.0 - (100.0 / (1.0 + relative_strength))
    rsi = rsi.mask((average_loss == 0.0) & (average_gain > 0.0), 100.0)
    rsi = rsi.mask((average_loss == 0.0) & (average_gain == 0.0), 50.0)
    out["rsi_14"] = rsi / 100.0

    rolling_low = low.rolling(20).min()
    rolling_high = high.rolling(20).max()
    range_width = (rolling_high - rolling_low).replace(0.0, np.nan)
    out["range_pos_20"] = (close - rolling_low) / range_width

    out["body_pct"] = (close - open_) / close.replace(0, np.nan)
    raw_volume_20 = volume.rolling(20).mean()
    volume_20 = raw_volume_20.replace(0.0, np.nan)
    volume_ratio = volume.rolling(5).mean() / volume_20 - 1.0
    out["volume_ratio_5_20"] = volume_ratio.mask(
        raw_volume_20.eq(0.0),
        0.0,
    )

    return out.loc[:, CHALLENGER_FEATURES].replace([np.inf, -np.inf], np.nan)


def make_labels(
    df: pd.DataFrame,
    horizon_bars: int = 1,
    return_threshold: float = 0.001,
) -> pd.Series:
    future_return = df["Close"].shift(-horizon_bars) / df["Close"] - 1.0
    labels = pd.Series(0, index=df.index, dtype="int8")
    labels.loc[future_return > return_threshold] = 1
    labels.loc[future_return < -return_threshold] = -1
    labels.loc[future_return.isna()] = pd.NA
    return labels.astype("Int8")

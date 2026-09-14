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
    vol_std = volume.rolling(20).std().replace(0, np.nan)
    out["volume_z20"] = (volume - vol_mean) / vol_std

    return out.replace([np.inf, -np.inf], np.nan)


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

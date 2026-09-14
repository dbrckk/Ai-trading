from __future__ import annotations

import pandas as pd

from .features import make_features, make_labels
from .specialist_experts import SpecialistDirectionModel


def specialist_return_series(
    df: pd.DataFrame,
    *,
    kind: str,
    return_threshold: float,
    horizon_bars: int = 1,
    train_fraction: float = 0.70,
) -> pd.Series:
    features = make_features(df)
    labels = make_labels(
        df,
        horizon_bars=horizon_bars,
        return_threshold=return_threshold,
    )
    usable = features.dropna().index.intersection(labels.dropna().index)
    if len(usable) < 120:
        raise ValueError("Need at least 120 usable bars")

    split = max(80, int(len(usable) * train_fraction))
    train_idx = usable[:split]
    test_idx = usable[split:]
    if len(test_idx) < 20:
        raise ValueError("Need at least 20 validation bars")

    model = SpecialistDirectionModel(kind)
    model.fit(features.loc[train_idx], labels.loc[train_idx])

    values: dict[pd.Timestamp, float] = {}
    for idx in test_idx[:-1]:
        pos = int(df.index.get_loc(idx))
        if pos + 1 >= len(df.index):
            continue
        next_idx = df.index[pos + 1]
        prediction = model.predict_one(features.loc[idx])
        market_return = float(df.at[next_idx, "Close"] / df.at[next_idx, "Open"] - 1.0)
        values[next_idx] = prediction.side * market_return

    return pd.Series(values, dtype=float).sort_index()


def equal_weight_pool_returns(series: dict[str, pd.Series]) -> pd.Series:
    if not series:
        raise ValueError("No active expert return series")
    frame = pd.DataFrame(series).dropna()
    if len(frame) < 20:
        raise ValueError("Need at least 20 aligned pool observations")
    return frame.mean(axis=1)

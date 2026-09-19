from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from .ensemble import EnsembleDirectionModel
from .features import FEATURES
from .model import Prediction
from .regime import detect_regime


@dataclass(frozen=True)
class ShadowChallengerResult:
    prediction: Prediction
    regime: str
    signal_time: str
    execution_time: str
    training_rows: int
    training_end: str
    realized_label: int | None


def evaluate_shadow_challenger(
    market: pd.DataFrame,
    features: pd.DataFrame,
    labels: pd.Series,
    execution_idx: object,
    *,
    horizon_bars: int = 1,
    min_train_rows: int = 100,
    random_state: int = 42,
) -> ShadowChallengerResult | None:
    """Evaluate a batch ensemble without allowing it to influence execution.

    Training rows are restricted so every training label is fully observable by
    the signal bar. This keeps the challenger suitable for shadow evaluation
    during paper trading and catch-up processing.
    """

    if horizon_bars < 1:
        raise ValueError("horizon_bars must be at least 1")
    if min_train_rows < 1:
        raise ValueError("min_train_rows must be at least 1")
    if execution_idx not in market.index:
        raise ValueError("execution index is not present in market data")

    execution_pos = int(market.index.get_loc(execution_idx))
    if execution_pos < 1:
        raise ValueError("execution index has no preceding signal bar")

    signal_pos = execution_pos - 1
    signal_idx = market.index[signal_pos]
    if signal_idx not in features.index:
        return None

    signal_row = features.loc[signal_idx, FEATURES]
    if signal_row.isna().any():
        return None

    last_train_pos = signal_pos - horizon_bars
    if last_train_pos < 0:
        return None

    allowed = set(market.index[: last_train_pos + 1])
    valid_feature_rows = features.loc[:, FEATURES].dropna().index
    labeled_rows = labels.dropna().index
    train_idx = [
        idx
        for idx in valid_feature_rows
        if idx in allowed and idx in labeled_rows
    ]
    if len(train_idx) < min_train_rows:
        return None

    model = EnsembleDirectionModel(random_state=random_state)
    model.fit(features.loc[train_idx], labels.loc[train_idx])

    regime = detect_regime(signal_row)
    prediction = model.predict_one(signal_row, regime)
    realized = labels.get(signal_idx)
    realized_label = int(realized) if pd.notna(realized) else None
    return ShadowChallengerResult(
        prediction=prediction,
        regime=regime.name,
        signal_time=str(signal_idx),
        execution_time=str(execution_idx),
        training_rows=len(train_idx),
        training_end=str(train_idx[-1]),
        realized_label=realized_label,
    )

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from .ensemble import EnsembleDirectionModel
from .features import FEATURES
from .model import Prediction
from .multi_timeframe_features import (
    MTF_CHALLENGER_FEATURES,
    adaptive_return_threshold,
    make_multi_timeframe_challenger_features,
    make_volatility_adaptive_labels,
)
from .regime import detect_regime


@dataclass(frozen=True)
class MultiTimeframeShadowResult:
    prediction: Prediction
    regime: str
    signal_time: str
    execution_time: str
    training_rows: int
    training_end: str
    realized_label: int
    horizon_bars: int
    horizon_minutes: int
    timeframes: tuple[str, ...]
    threshold_at_signal: float
    minimum_threshold: float
    atr_multiplier: float
    feature_count: int


def select_observable_execution_target(
    market: pd.DataFrame,
    eligible: tuple[object, ...],
    current_execution_idx: object,
    *,
    horizon_bars: int = 3,
) -> object | None:
    """Select the newest shadow target whose horizon is observable now.

    The chosen target is delayed relative to the current production target, so
    its full forward outcome is known without using information unavailable at
    the time the shadow prediction would have been made.
    """

    if horizon_bars < 1:
        raise ValueError("horizon_bars must be at least 1")
    if current_execution_idx not in market.index:
        raise ValueError("current execution index is not present in market data")

    current_pos = int(market.index.get_loc(current_execution_idx))
    max_execution_pos = current_pos - (horizon_bars - 1)
    if max_execution_pos < 1:
        return None

    candidate = None
    for execution_idx in eligible:
        execution_pos = int(market.index.get_loc(execution_idx))
        if execution_pos <= max_execution_pos:
            candidate = execution_idx
        else:
            break
    return candidate


def evaluate_multi_timeframe_shadow(
    market: pd.DataFrame,
    authoritative_features: pd.DataFrame,
    execution_idx: object,
    *,
    horizon_bars: int = 3,
    min_train_rows: int = 500,
    max_train_rows: int = 2000,
    minimum_threshold: float = 0.001,
    atr_multiplier: float = 0.25,
    random_state: int = 42,
) -> MultiTimeframeShadowResult | None:
    """Evaluate a 5m/15m/1h/4h ensemble without controlling execution."""

    if horizon_bars < 1:
        raise ValueError("horizon_bars must be at least 1")
    if min_train_rows < 1:
        raise ValueError("min_train_rows must be at least 1")
    if max_train_rows < min_train_rows:
        raise ValueError("max_train_rows must be >= min_train_rows")
    if execution_idx not in market.index:
        raise ValueError("execution index is not present in market data")

    execution_pos = int(market.index.get_loc(execution_idx))
    if execution_pos < 1:
        return None
    signal_pos = execution_pos - 1
    signal_idx = market.index[signal_pos]

    mtf_features = make_multi_timeframe_challenger_features(market)
    mtf_features.loc[:, FEATURES] = authoritative_features.loc[:, FEATURES]
    signal_row = mtf_features.loc[signal_idx, MTF_CHALLENGER_FEATURES]
    if signal_row.isna().any():
        return None

    labels = make_volatility_adaptive_labels(
        market,
        horizon_bars=horizon_bars,
        minimum_threshold=minimum_threshold,
        atr_multiplier=atr_multiplier,
    )
    threshold = adaptive_return_threshold(
        market,
        minimum_threshold=minimum_threshold,
        atr_multiplier=atr_multiplier,
    )

    last_train_pos = signal_pos - horizon_bars
    if last_train_pos < 0:
        return None

    allowed = set(market.index[: last_train_pos + 1])
    valid_feature_rows = mtf_features.loc[:, MTF_CHALLENGER_FEATURES].dropna().index
    labeled_rows = labels.dropna().index
    train_idx = [
        idx
        for idx in valid_feature_rows
        if idx in allowed and idx in labeled_rows
    ]
    if len(train_idx) < min_train_rows:
        return None
    train_idx = train_idx[-max_train_rows:]

    realized = labels.get(signal_idx)
    threshold_at_signal = threshold.get(signal_idx)
    if pd.isna(realized) or pd.isna(threshold_at_signal):
        return None

    model = EnsembleDirectionModel(
        random_state=random_state,
        feature_names=MTF_CHALLENGER_FEATURES,
    )
    model.fit(mtf_features.loc[train_idx], labels.loc[train_idx])

    regime = detect_regime(signal_row)
    prediction = model.predict_one(signal_row, regime)
    return MultiTimeframeShadowResult(
        prediction=prediction,
        regime=regime.name,
        signal_time=str(signal_idx),
        execution_time=str(execution_idx),
        training_rows=len(train_idx),
        training_end=str(train_idx[-1]),
        realized_label=int(realized),
        horizon_bars=horizon_bars,
        horizon_minutes=horizon_bars * 5,
        timeframes=("5m", "15m", "1h", "4h"),
        threshold_at_signal=float(threshold_at_signal),
        minimum_threshold=minimum_threshold,
        atr_multiplier=atr_multiplier,
        feature_count=len(MTF_CHALLENGER_FEATURES),
    )

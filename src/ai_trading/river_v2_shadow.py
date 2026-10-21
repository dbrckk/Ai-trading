"""Opt-in River-v2 forward observer and delayed, audit-only label comparison.

Neither the observer nor its quality calculation can place or approve trades.
A forward observation is never given future market candles or future labels.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, datetime
from math import isfinite
from typing import Any

import pandas as pd

from .features import FEATURES, make_features, make_labels
from .model import Prediction
from .model_quality import ModelQuality, evaluate_model_quality
from .online import RiverMulticlassDirectionModel
from .research_model_codec import RESEARCH_MODEL_FORMAT, RESEARCH_MODEL_VERSION

_INTERVAL = pd.Timedelta(minutes=5)


@dataclass(frozen=True)
class RiverV2ForwardObservation:
    prediction: Prediction
    signal_time: str
    signal_close: float
    observed_at_utc: str
    training_rows: int
    training_end: str
    horizon_bars: int
    return_threshold: float
    min_confidence: float
    gated_side: int
    model_format: str = RESEARCH_MODEL_FORMAT
    model_version: int = RESEARCH_MODEL_VERSION


@dataclass(frozen=True)
class RiverV2ForwardComparison:
    observations: int
    pending: int
    short_predictions: int
    river: ModelQuality
    river_v2: ModelQuality

    @property
    def score_delta(self) -> float | None:
        if self.observations < 5:
            return None
        return self.river_v2.score - self.river.score


def observe_river_v2_forward(
    market: pd.DataFrame,
    *,
    horizon_bars: int,
    return_threshold: float,
    min_confidence: float,
    now: datetime | None = None,
    min_train_rows: int = 100,
    max_train_rows: int = 384,
) -> RiverV2ForwardObservation | None:
    """Predict only from the latest *completed, recent* five-minute signal.

    The current market's last row must be a fully closed candle. The next
    candle is not present. Older/catch-up observations are deliberately
    skipped to avoid representing retrospective predictions as forward ones.
    """
    if horizon_bars < 1 or not 0 <= return_threshold:
        raise ValueError("invalid research label horizon/threshold")
    if not 0 <= min_confidence <= 1 or min_train_rows < 1:
        raise ValueError("invalid research confidence/training minimum")
    if max_train_rows < min_train_rows:
        raise ValueError("research training window must contain the minimum")
    if market.empty or not isinstance(market.index, pd.DatetimeIndex):
        return None
    if (
        market.index.has_duplicates
        or market.index.hasnans
        or not market.index.is_monotonic_increasing
    ):
        return None
    signal_time = pd.Timestamp(market.index[-1])
    if signal_time.tzinfo is None:
        return None
    signal_utc = signal_time.tz_convert("UTC")
    current = pd.Timestamp(now or datetime.now(UTC))
    if current.tzinfo is None:
        raise ValueError("now must be timezone-aware")
    current = current.tz_convert("UTC")
    age = current - (signal_utc + _INTERVAL)
    # Allow a short provider delay, but never score signals observed after
    # their next five-minute outcome could already have completed.
    if age < pd.Timedelta(0) or age >= _INTERVAL:
        return None

    # Slice first: even accidental future columns cannot reach the trainer.
    observed = market.iloc[:].copy()
    features = make_features(observed)
    labels = make_labels(
        observed,
        horizon_bars=horizon_bars,
        return_threshold=return_threshold,
    )
    last_train_pos = len(observed) - 1 - horizon_bars
    if last_train_pos < 0:
        return None
    candidates = [
        pos
        for pos in range(last_train_pos + 1)
        if pd.notna(labels.iloc[pos])
        and features.iloc[pos].loc[FEATURES].notna().all()
    ]
    if len(candidates) < min_train_rows:
        return None

    signal_row = features.iloc[-1].loc[FEATURES]
    if not signal_row.notna().all():
        return None
    train_positions = candidates[-max_train_rows:]
    model = RiverMulticlassDirectionModel()
    for pos in train_positions:
        model.learn_one(features.iloc[pos].loc[FEATURES], int(labels.iloc[pos]))
    prediction = model.predict_one(signal_row)
    if (
        prediction.side not in (-1, 0, 1)
        or not isfinite(prediction.confidence)
        or not 0 <= prediction.confidence <= 1
        or set(prediction.probabilities) != {-1, 0, 1}
        or any(
            not isfinite(p) or p < 0 or p > 1
            for p in prediction.probabilities.values()
        )
        or abs(sum(prediction.probabilities.values()) - 1.0) > 1e-6
    ):
        return None  # Fail open for paper execution, closed for shadow evidence.
    signal_close = float(observed["Close"].iloc[-1])
    if not isfinite(signal_close) or signal_close <= 0:
        return None
    return RiverV2ForwardObservation(
        prediction=prediction,
        signal_time=str(market.index[-1]),
        signal_close=signal_close,
        observed_at_utc=current.isoformat(),
        training_rows=len(train_positions),
        training_end=str(market.index[train_positions[-1]]),
        horizon_bars=horizon_bars,
        return_threshold=return_threshold,
        min_confidence=min_confidence,
        gated_side=prediction.side if prediction.confidence >= min_confidence else 0,
    )


def compare_river_v2_forward_audit_payloads(
    payloads: Iterable[dict[str, Any]],
) -> RiverV2ForwardComparison:
    """Evaluate only matured, matched v1/v2 signals stored on different cycles.

    v2 predictions were committed in an earlier audit row. The v1
    `execution_close` and v1 prediction arrive in a later audit row.
    The comparison is directional accuracy, NOT a tradable return backtest.
    """
    audit_rows = tuple(payloads)
    v1_by_signal: dict[str, dict[str, Any]] = {}
    for payload in audit_rows:
        signal = payload.get("signal_time")
        if isinstance(signal, str) and "prediction" in payload:
            v1_by_signal.setdefault(signal, payload)

    sides_v1: list[int] = []
    conf_v1: list[float] = []
    sides_v2: list[int] = []
    conf_v2: list[float] = []
    labels: list[int] = []
    pending = 0
    shorts = 0
    seen: set[str] = set()

    for payload in audit_rows:
        shadow = payload.get("river_v2_shadow")
        if not isinstance(shadow, dict):
            continue
        signal = shadow.get("signal_time")
        if not isinstance(signal, str) or signal in seen:
            continue
        seen.add(signal)
        later = v1_by_signal.get(signal)
        if later is None:
            pending += 1
            continue
        try:
            if shadow["model_format"] != RESEARCH_MODEL_FORMAT or (
                int(shadow["model_version"]) != RESEARCH_MODEL_VERSION
            ):
                continue
            if int(shadow["horizon_bars"]) != 1:
                continue  # This matching is defined for one-bar outcomes only.
            signal_time = pd.Timestamp(signal)
            execution_time = pd.Timestamp(later["execution_time"])
            observed_time = pd.Timestamp(shadow["observed_at_utc"])
            if any(t.tzinfo is None for t in (signal_time, execution_time, observed_time)):
                continue
            signal_time = signal_time.tz_convert("UTC")
            execution_time = execution_time.tz_convert("UTC")
            observed_time = observed_time.tz_convert("UTC")
            if execution_time != signal_time + _INTERVAL:
                continue  # No imputed result across session/provider gaps.
            if not signal_time + _INTERVAL <= observed_time < execution_time + _INTERVAL:
                continue  # Must have been observed before the outcome closed.
            signal_close = float(shadow["signal_close"])
            next_close = float(later["execution_close"])
            threshold = float(shadow["return_threshold"])
            if not all(isfinite(v) for v in (signal_close, next_close, threshold)):
                continue
            if signal_close <= 0 or next_close <= 0 or threshold < 0:
                continue
            v1 = later["prediction"]
            v2 = shadow["prediction"]
            side_v1, side_v2 = int(v1["side"]), int(v2["side"])
            confidence_v1, confidence_v2 = float(v1["confidence"]), float(v2["confidence"])
            minimum = float(shadow["min_confidence"])
            if (side_v1 not in (-1, 0, 1) or side_v2 not in (-1, 0, 1)
                or not all(isfinite(v) and 0 <= v <= 1
                           for v in (confidence_v1, confidence_v2, minimum))):
                continue
        except (KeyError, TypeError, ValueError, OverflowError):
            continue

        realized_return = next_close / signal_close - 1.0
        label = int(realized_return > threshold) - int(realized_return < -threshold)
        # Compare identical raw side/confidence definitions for both models.
        # Minimum confidence applies only to the separate directional count.
        sides_v1.append(side_v1)
        conf_v1.append(confidence_v1)
        sides_v2.append(side_v2)
        conf_v2.append(confidence_v2)
        labels.append(label)
        shorts += int(side_v2 == -1 and confidence_v2 >= minimum)

    def quality(sides: list[int], confidences: list[float]) -> ModelQuality:
        return evaluate_model_quality(
            pd.Series(sides, dtype="int64"),
            pd.Series(confidences, dtype="float64"),
            pd.Series(labels, dtype="int64"),
        )

    return RiverV2ForwardComparison(
        observations=len(labels),
        pending=pending,
        short_predictions=shorts,
        river=quality(sides_v1, conf_v1),
        river_v2=quality(sides_v2, conf_v2),
    )

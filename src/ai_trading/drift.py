from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from .features import FEATURES


@dataclass(frozen=True)
class DriftReport:
    feature_drift_score: float
    return_drift_score: float
    drifted: bool
    reasons: tuple[str, ...]


def _standardized_mean_shift(reference: pd.Series, recent: pd.Series) -> float:
    ref = reference.astype(float).dropna()
    cur = recent.astype(float).dropna()
    if len(ref) < 20 or len(cur) < 10:
        return 0.0

    scale = float(ref.std(ddof=1))
    if not np.isfinite(scale) or scale < 1e-12:
        scale = 1e-12
    return abs(float(cur.mean() - ref.mean())) / scale


def detect_drift(
    reference_features: pd.DataFrame,
    recent_features: pd.DataFrame,
    reference_returns: pd.Series,
    recent_returns: pd.Series,
    *,
    feature_threshold: float = 1.5,
    return_threshold: float = 1.0,
) -> DriftReport:
    feature_scores = [
        _standardized_mean_shift(reference_features[name], recent_features[name])
        for name in FEATURES
        if name in reference_features.columns and name in recent_features.columns
    ]
    feature_score = max(feature_scores, default=0.0)
    return_score = _standardized_mean_shift(reference_returns, recent_returns)

    reasons: list[str] = []
    if feature_score >= feature_threshold:
        reasons.append("feature distribution drift")
    if return_score >= return_threshold:
        reasons.append("return distribution drift")

    return DriftReport(
        feature_drift_score=float(feature_score),
        return_drift_score=float(return_score),
        drifted=bool(reasons),
        reasons=tuple(reasons),
    )

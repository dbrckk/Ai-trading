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



@dataclass(frozen=True)
class DistributionDriftReport:
    max_psi: float
    mean_psi: float
    correlation_shift: float
    risk_multiplier: float
    retrain_requested: bool
    drifted_features: tuple[str, ...]


def _population_stability_index(
    reference: pd.Series,
    recent: pd.Series,
    *,
    bins: int = 10,
) -> float:
    ref = reference.astype(float).replace([np.inf, -np.inf], np.nan).dropna()
    cur = recent.astype(float).replace([np.inf, -np.inf], np.nan).dropna()
    if len(ref) < 50 or len(cur) < 20:
        return 0.0

    quantiles = np.unique(
        np.quantile(ref, np.linspace(0.0, 1.0, bins + 1))
    )
    if len(quantiles) < 3:
        return 0.0
    quantiles[0] = -np.inf
    quantiles[-1] = np.inf

    ref_bins = pd.cut(ref, bins=quantiles, include_lowest=True)
    cur_bins = pd.cut(cur, bins=quantiles, include_lowest=True)

    ref_freq = ref_bins.value_counts(sort=False, normalize=True)
    cur_freq = cur_bins.value_counts(sort=False, normalize=True).reindex(
        ref_freq.index,
        fill_value=0.0,
    )

    epsilon = 1e-6
    ref_values = np.clip(ref_freq.to_numpy(dtype=float), epsilon, None)
    cur_values = np.clip(cur_freq.to_numpy(dtype=float), epsilon, None)
    return float(
        np.sum((cur_values - ref_values) * np.log(cur_values / ref_values))
    )


def detect_distribution_drift(
    reference_features: pd.DataFrame,
    recent_features: pd.DataFrame,
    *,
    psi_warning: float = 0.10,
    psi_retrain: float = 0.25,
    correlation_warning: float = 0.35,
) -> DistributionDriftReport:
    common = [
        name
        for name in FEATURES
        if name in reference_features.columns and name in recent_features.columns
    ]
    if not common:
        return DistributionDriftReport(0.0, 0.0, 0.0, 1.0, False, ())

    psi_by_feature = {
        name: _population_stability_index(
            reference_features[name],
            recent_features[name],
        )
        for name in common
    }
    max_psi = max(psi_by_feature.values(), default=0.0)
    mean_psi = (
        sum(psi_by_feature.values()) / len(psi_by_feature)
        if psi_by_feature
        else 0.0
    )

    ref_corr = reference_features[common].astype(float).corr().fillna(0.0)
    cur_corr = recent_features[common].astype(float).corr().fillna(0.0)
    correlation_shift = float(
        np.abs(ref_corr.to_numpy() - cur_corr.to_numpy()).mean()
    )

    drifted = tuple(
        sorted(
            name
            for name, score in psi_by_feature.items()
            if score >= psi_warning
        )
    )
    severity = max(
        max_psi / max(psi_retrain, 1e-9),
        correlation_shift / max(correlation_warning, 1e-9),
    )
    risk_multiplier = float(np.clip(1.0 - 0.5 * severity, 0.25, 1.0))
    retrain_requested = bool(
        max_psi >= psi_retrain
        or correlation_shift >= correlation_warning
    )

    return DistributionDriftReport(
        max_psi=float(max_psi),
        mean_psi=float(mean_psi),
        correlation_shift=correlation_shift,
        risk_multiplier=risk_multiplier,
        retrain_requested=retrain_requested,
        drifted_features=drifted,
    )

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .model import Prediction
from .quality_store import QualityRecord


@dataclass(frozen=True)
class CalibrationReport:
    raw_confidence: float
    calibrated_confidence: float
    expected_calibration_error: float
    observations: int


def _bin_index(confidence: float, bins: int) -> int:
    return min(bins - 1, max(0, int(float(confidence) * bins)))


def calibration_report(
    raw_confidence: float,
    record: QualityRecord | None,
    *,
    bins: int = 10,
    prior_strength: float = 5.0,
) -> CalibrationReport:
    if record is None or len(record.labels) < 10:
        return CalibrationReport(
            raw_confidence=float(raw_confidence),
            calibrated_confidence=float(raw_confidence),
            expected_calibration_error=0.0,
            observations=0 if record is None else len(record.labels),
        )

    confidences = np.asarray(record.confidences, dtype=float)
    predictions = np.asarray(record.predictions, dtype=int)
    labels = np.asarray(record.labels, dtype=int)
    correct = (predictions == labels).astype(float)

    bin_ids = np.asarray([_bin_index(value, bins) for value in confidences])
    target_bin = _bin_index(raw_confidence, bins)
    mask = bin_ids == target_bin

    if int(mask.sum()) == 0:
        calibrated = float(raw_confidence)
    else:
        empirical_correct = float(correct[mask].sum())
        count = int(mask.sum())
        calibrated = (
            empirical_correct + prior_strength * float(raw_confidence)
        ) / (count + prior_strength)

    ece = 0.0
    total = len(confidences)
    for bin_id in range(bins):
        current = bin_ids == bin_id
        count = int(current.sum())
        if count == 0:
            continue
        mean_confidence = float(confidences[current].mean())
        accuracy = float(correct[current].mean())
        ece += (count / total) * abs(accuracy - mean_confidence)

    return CalibrationReport(
        raw_confidence=float(raw_confidence),
        calibrated_confidence=float(np.clip(calibrated, 0.0, 1.0)),
        expected_calibration_error=float(ece),
        observations=total,
    )


def conservatively_calibrate_prediction(
    prediction: Prediction,
    record: QualityRecord | None,
    *,
    bins: int = 10,
) -> tuple[Prediction, CalibrationReport]:
    report = calibration_report(
        prediction.confidence,
        record,
        bins=bins,
    )

    raw = max(1e-12, float(prediction.confidence))
    shrink = min(1.0, report.calibrated_confidence / raw)
    uniform = 1.0 / 3.0

    probabilities = {
        side: uniform + shrink * (float(probability) - uniform)
        for side, probability in prediction.probabilities.items()
    }
    for side in (-1, 0, 1):
        probabilities.setdefault(side, uniform)

    total = sum(probabilities.values())
    probabilities = {
        side: float(max(0.0, probability) / total)
        for side, probability in probabilities.items()
    }
    side = max(probabilities, key=probabilities.get)

    calibrated_prediction = Prediction(
        side=int(side),
        confidence=float(probabilities[side]),
        probabilities=probabilities,
    )
    return calibrated_prediction, report

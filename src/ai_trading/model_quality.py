from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class ModelQuality:
    score: float
    accuracy: float
    brier: float
    directional_edge: float
    observations: int


def evaluate_model_quality(
    predicted_sides: pd.Series,
    confidences: pd.Series,
    realized_labels: pd.Series,
) -> ModelQuality:
    frame = pd.concat(
        [
            predicted_sides.rename("pred"),
            confidences.rename("confidence"),
            realized_labels.rename("label"),
        ],
        axis=1,
    ).dropna()

    if len(frame) < 5:
        return ModelQuality(0.0, 0.0, 1.0, 0.0, len(frame))

    pred = frame["pred"].astype(int)
    label = frame["label"].astype(int)
    confidence = frame["confidence"].astype(float).clip(0.0, 1.0)

    correct = (pred == label).astype(float)
    accuracy = float(correct.mean())

    # Treat confidence as probability assigned to the predicted class.
    brier = float(((confidence - correct) ** 2).mean())

    active = frame[pred != 0]
    if active.empty:
        edge = 0.0
    else:
        edge = float((active["pred"].astype(int) == active["label"].astype(int)).mean() - 0.5)

    score = (
        0.50 * accuracy
        + 0.30 * max(0.0, 1.0 - brier)
        + 0.20 * max(0.0, edge + 0.5)
    )
    return ModelQuality(
        score=float(np.clip(score, 0.0, 1.0)),
        accuracy=accuracy,
        brier=brier,
        directional_edge=edge,
        observations=len(frame),
    )

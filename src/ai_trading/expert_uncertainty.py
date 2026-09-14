from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .model import Prediction


@dataclass(frozen=True)
class ExpertUncertainty:
    disagreement: float
    consensus_confidence: float
    risk_multiplier: float
    experts: int


def measure_expert_uncertainty(
    predictions: dict[str, Prediction],
    weights: dict[str, float] | None = None,
    *,
    min_risk_multiplier: float = 0.25,
) -> ExpertUncertainty:
    if not predictions:
        return ExpertUncertainty(1.0, 0.0, min_risk_multiplier, 0)

    names = list(predictions)
    if weights is None:
        normalized = {name: 1.0 / len(names) for name in names}
    else:
        raw = {name: max(0.0, float(weights.get(name, 0.0))) for name in names}
        total = sum(raw.values())
        normalized = (
            {name: value / total for name, value in raw.items()}
            if total > 0
            else {name: 1.0 / len(names) for name in names}
        )

    classes = (-1, 0, 1)
    consensus = np.zeros(3, dtype=float)
    vectors: dict[str, np.ndarray] = {}

    for name in names:
        vector = np.asarray(
            [float(predictions[name].probabilities.get(side, 0.0)) for side in classes],
            dtype=float,
        )
        total = float(vector.sum())
        if total <= 0:
            vector = np.full(3, 1.0 / 3.0)
        else:
            vector = vector / total
        vectors[name] = vector
        consensus += normalized[name] * vector

    disagreement = 0.0
    for name, vector in vectors.items():
        # Total variation distance is bounded to [0, 1].
        tv = 0.5 * float(np.abs(vector - consensus).sum())
        disagreement += normalized[name] * tv

    risk_multiplier = max(
        min_risk_multiplier,
        min(1.0, 1.0 - disagreement),
    )
    consensus_confidence = float(consensus.max())

    return ExpertUncertainty(
        disagreement=float(disagreement),
        consensus_confidence=consensus_confidence,
        risk_multiplier=float(risk_multiplier),
        experts=len(names),
    )

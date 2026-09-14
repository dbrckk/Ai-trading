from __future__ import annotations

from dataclasses import dataclass

from .model import Prediction


@dataclass(frozen=True)
class BlendComponent:
    name: str
    prediction: Prediction
    quality_score: float


def blend_predictions(
    components: list[BlendComponent],
    *,
    min_quality: float = 0.05,
) -> Prediction:
    if not components:
        raise ValueError("Need at least one prediction component")

    aggregate = {-1: 0.0, 0: 0.0, 1: 0.0}
    total_weight = 0.0

    for component in components:
        weight = max(min_quality, float(component.quality_score))
        total_weight += weight
        for side in aggregate:
            aggregate[side] += weight * float(component.prediction.probabilities.get(side, 0.0))

    if total_weight <= 0:
        return Prediction(side=0, confidence=1.0, probabilities={-1: 0.0, 0: 1.0, 1: 0.0})

    aggregate = {side: value / total_weight for side, value in aggregate.items()}
    side = max(aggregate, key=aggregate.get)
    return Prediction(
        side=side,
        confidence=float(aggregate[side]),
        probabilities={k: float(v) for k, v in aggregate.items()},
    )

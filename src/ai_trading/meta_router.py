from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .model import Prediction


@dataclass(frozen=True)
class MetaContext:
    symbol: str
    regime: str
    volatility_bucket: str
    drawdown_bucket: str


@dataclass(frozen=True)
class ModelContextStats:
    wins: int = 0
    losses: int = 0
    cumulative_edge: float = 0.0

    @property
    def observations(self) -> int:
        return self.wins + self.losses

    @property
    def success_rate(self) -> float:
        return (self.wins + 1.0) / (self.observations + 2.0)

    @property
    def mean_edge(self) -> float:
        if self.observations == 0:
            return 0.0
        return self.cumulative_edge / self.observations

    @property
    def score(self) -> float:
        return float(np.clip(0.75 * self.success_rate + 0.25 * (0.5 + self.mean_edge), 0.0, 1.0))


@dataclass(frozen=True)
class RoutedPrediction:
    prediction: Prediction
    weights: dict[str, float]


def context_key(context: MetaContext) -> str:
    return (
        f"{context.symbol}|{context.regime}|"
        f"{context.volatility_bucket}|{context.drawdown_bucket}"
    )


def route_predictions(
    predictions: dict[str, Prediction],
    scores: dict[str, float],
    *,
    min_weight: float = 0.05,
) -> RoutedPrediction:
    if not predictions:
        raise ValueError("predictions cannot be empty")

    raw = {
        name: max(min_weight, float(scores.get(name, 0.5)))
        for name in predictions
    }
    total = sum(raw.values())
    weights = {name: value / total for name, value in raw.items()}

    aggregate = {-1: 0.0, 0: 0.0, 1: 0.0}
    for name, prediction in predictions.items():
        weight = weights[name]
        for side in aggregate:
            aggregate[side] += weight * float(prediction.probabilities.get(side, 0.0))

    side = max(aggregate, key=aggregate.get)
    return RoutedPrediction(
        prediction=Prediction(
            side=side,
            confidence=float(aggregate[side]),
            probabilities={k: float(v) for k, v in aggregate.items()},
        ),
        weights=weights,
    )

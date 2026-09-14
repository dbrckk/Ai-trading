from __future__ import annotations

from dataclasses import dataclass

import pandas as pd
from river import linear_model, preprocessing

from .features import FEATURES
from .model import Prediction


@dataclass
class OnlineLearningStats:
    observations: int = 0
    correct: int = 0

    @property
    def accuracy(self) -> float:
        if self.observations == 0:
            return 0.0
        return self.correct / self.observations


class RiverDirectionModel:
    """True incremental classifier updated one labeled observation at a time."""

    def __init__(self) -> None:
        self.model = preprocessing.StandardScaler() | linear_model.LogisticRegression()
        self.stats = OnlineLearningStats()
        self._classes = (-1, 0, 1)

    @staticmethod
    def _x(row: pd.Series) -> dict[str, float]:
        return {name: float(row[name]) for name in FEATURES}

    def learn_one(self, row: pd.Series, label: int) -> None:
        if label not in self._classes:
            raise ValueError("label must be -1, 0, or 1")
        x = self._x(row)
        before = self.predict_one(row)
        self.model.learn_one(x, label)
        self.stats.observations += 1
        if before.side == label:
            self.stats.correct += 1

    def predict_one(self, row: pd.Series) -> Prediction:
        x = self._x(row)
        raw = self.model.predict_proba_one(x)
        probabilities = {cls: float(raw.get(cls, 0.0)) for cls in self._classes}
        total = sum(probabilities.values())

        if total <= 0:
            probabilities = {-1: 0.0, 0: 1.0, 1: 0.0}
        else:
            probabilities = {k: v / total for k, v in probabilities.items()}

        side = max(probabilities, key=probabilities.get)
        return Prediction(
            side=side,
            confidence=probabilities[side],
            probabilities=probabilities,
        )

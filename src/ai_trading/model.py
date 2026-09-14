from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from sklearn.linear_model import SGDClassifier
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from .features import FEATURES


@dataclass(frozen=True)
class Prediction:
    side: int
    confidence: float
    probabilities: dict[int, float]


class OnlineDirectionModel:
    """Incrementally trainable three-class direction model: short/flat/long."""

    classes = np.array([-1, 0, 1], dtype=int)

    def __init__(self, random_state: int = 42) -> None:
        self.pipeline = Pipeline(
            [
                ("scale", StandardScaler()),
                (
                    "model",
                    SGDClassifier(
                        loss="log_loss",
                        penalty="elasticnet",
                        alpha=1e-4,
                        l1_ratio=0.10,
                        random_state=random_state,
                        class_weight="balanced",
                    ),
                ),
            ]
        )
        self._fitted = False

    def fit(self, x: pd.DataFrame, y: pd.Series) -> None:
        x2 = x.loc[:, FEATURES].dropna()
        y2 = y.reindex(x2.index).dropna().astype(int)
        x2 = x2.loc[y2.index]
        if len(x2) < 50:
            raise ValueError("Need at least 50 labeled rows to train")
        self.pipeline.fit(x2, y2)
        self._fitted = True

    def predict_one(self, row: pd.Series) -> Prediction:
        if not self._fitted:
            raise RuntimeError("Model is not trained")
        x = pd.DataFrame([row.loc[FEATURES].astype(float).to_dict()])
        proba = self.pipeline.predict_proba(x)[0]
        model = self.pipeline.named_steps["model"]
        mapping = {int(cls): float(p) for cls, p in zip(model.classes_, proba, strict=True)}
        side = max(mapping, key=mapping.get)
        return Prediction(side=side, confidence=mapping[side], probabilities=mapping)

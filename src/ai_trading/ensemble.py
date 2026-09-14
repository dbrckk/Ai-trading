from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier, RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from .features import FEATURES
from .model import Prediction
from .regime import MarketRegime


@dataclass
class _Member:
    name: str
    model: object
    weight: float


class EnsembleDirectionModel:
    classes = np.array([-1, 0, 1], dtype=int)

    def __init__(self, random_state: int = 42) -> None:
        self.members = [
            _Member(
                "logistic",
                Pipeline(
                    [
                        ("scale", StandardScaler()),
                        (
                            "model",
                            LogisticRegression(
                                max_iter=1000,
                                class_weight="balanced",
                                random_state=random_state,
                            ),
                        ),
                    ]
                ),
                1.0,
            ),
            _Member(
                "random_forest",
                RandomForestClassifier(
                    n_estimators=200,
                    max_depth=6,
                    min_samples_leaf=8,
                    class_weight="balanced_subsample",
                    random_state=random_state,
                    n_jobs=1,
                ),
                1.0,
            ),
            _Member(
                "hist_gb",
                HistGradientBoostingClassifier(
                    learning_rate=0.05,
                    max_depth=5,
                    max_iter=150,
                    random_state=random_state,
                ),
                1.0,
            ),
        ]
        self._fitted = False

    def fit(self, x: pd.DataFrame, y: pd.Series) -> None:
        x2 = x.loc[:, FEATURES].dropna()
        y2 = y.reindex(x2.index).dropna().astype(int)
        x2 = x2.loc[y2.index]
        if len(x2) < 100:
            raise ValueError("Need at least 100 labeled rows to train ensemble")

        for member in self.members:
            member.model.fit(x2, y2)
        self._fitted = True

    def _regime_weights(self, regime: MarketRegime) -> dict[str, float]:
        weights = {member.name: member.weight for member in self.members}

        if regime.trend == "sideways":
            weights["random_forest"] *= 1.15
            weights["hist_gb"] *= 1.10
        else:
            weights["logistic"] *= 1.10
            weights["hist_gb"] *= 1.15

        if regime.volatility == "high_vol":
            weights["random_forest"] *= 1.10
            weights["logistic"] *= 0.90

        total = sum(weights.values())
        return {k: v / total for k, v in weights.items()}

    def predict_one(self, row: pd.Series, regime: MarketRegime) -> Prediction:
        if not self._fitted:
            raise RuntimeError("Ensemble is not trained")

        x = pd.DataFrame([row.loc[FEATURES].astype(float).to_dict()])
        weights = self._regime_weights(regime)
        aggregate = {-1: 0.0, 0: 0.0, 1: 0.0}

        for member in self.members:
            proba = member.model.predict_proba(x)[0]
            model_classes = member.model.classes_
            for cls, p in zip(model_classes, proba, strict=True):
                aggregate[int(cls)] += weights[member.name] * float(p)

        side = max(aggregate, key=aggregate.get)
        return Prediction(
            side=side,
            confidence=float(aggregate[side]),
            probabilities={k: float(v) for k, v in aggregate.items()},
        )

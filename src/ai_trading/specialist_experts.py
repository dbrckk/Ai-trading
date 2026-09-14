from __future__ import annotations

from dataclasses import dataclass

import pandas as pd
from sklearn.ensemble import ExtraTreesClassifier, HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from .features import FEATURES
from .model import Prediction
from .regime import MarketRegime


@dataclass(frozen=True)
class SpecialistSpec:
    name: str
    target_regimes: tuple[str, ...]


class SpecialistDirectionModel:
    def __init__(self, kind: str, random_state: int = 42) -> None:
        self.kind = kind
        if kind == "trend":
            self.model = Pipeline(
                [
                    ("scale", StandardScaler()),
                    (
                        "model",
                        LogisticRegression(
                            C=0.5,
                            max_iter=1000,
                            class_weight="balanced",
                            random_state=random_state,
                        ),
                    ),
                ]
            )
        elif kind == "range":
            self.model = ExtraTreesClassifier(
                n_estimators=250,
                max_depth=8,
                min_samples_leaf=6,
                class_weight="balanced",
                random_state=random_state,
                n_jobs=1,
            )
        elif kind == "high_vol":
            self.model = HistGradientBoostingClassifier(
                learning_rate=0.04,
                max_depth=4,
                max_iter=180,
                random_state=random_state,
            )
        else:
            raise ValueError(f"Unknown specialist kind: {kind}")
        self._fitted = False

    def fit(self, x: pd.DataFrame, y: pd.Series) -> None:
        x2 = x.loc[:, FEATURES].dropna()
        y2 = y.reindex(x2.index).dropna().astype(int)
        x2 = x2.loc[y2.index]
        if len(x2) < 80:
            raise ValueError("Need at least 80 labeled rows to train specialist")
        self.model.fit(x2, y2)
        self._fitted = True

    def supports(self, regime: MarketRegime) -> bool:
        if self.kind == "trend":
            return regime.trend in {"bull", "bear"}
        if self.kind == "range":
            return regime.trend == "sideways"
        if self.kind == "high_vol":
            return regime.volatility == "high_vol"
        return False

    def predict_one(self, row: pd.Series) -> Prediction:
        if not self._fitted:
            raise RuntimeError("Specialist is not trained")
        x = pd.DataFrame([row.loc[FEATURES].astype(float).to_dict()])
        proba = self.model.predict_proba(x)[0]
        mapping = {
            int(cls): float(p)
            for cls, p in zip(self.model.classes_, proba, strict=True)
        }
        for cls in (-1, 0, 1):
            mapping.setdefault(cls, 0.0)
        side = max(mapping, key=mapping.get)
        return Prediction(side=side, confidence=mapping[side], probabilities=mapping)

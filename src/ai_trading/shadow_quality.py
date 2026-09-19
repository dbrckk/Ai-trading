from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any

import pandas as pd

from .model_quality import ModelQuality, evaluate_model_quality


@dataclass(frozen=True)
class ShadowQualityComparison:
    observations: int
    river: ModelQuality
    challenger: ModelQuality

    @property
    def score_delta(self) -> float:
        return float(self.challenger.score - self.river.score)


def _empty_quality() -> ModelQuality:
    return ModelQuality(
        score=0.0,
        accuracy=0.0,
        brier=1.0,
        directional_edge=0.0,
        observations=0,
    )


def compare_shadow_audit_payloads(
    payloads: Iterable[dict[str, Any]],
) -> ShadowQualityComparison:
    river_sides: list[int] = []
    river_confidences: list[float] = []
    challenger_sides: list[int] = []
    challenger_confidences: list[float] = []
    labels: list[int] = []

    for payload in payloads:
        shadow = payload.get("shadow_challenger")
        river_prediction = payload.get("prediction")
        if not isinstance(shadow, dict) or not isinstance(river_prediction, dict):
            continue
        challenger_prediction = shadow.get("prediction")
        realized = shadow.get("realized_label")
        if not isinstance(challenger_prediction, dict) or realized is None:
            continue
        try:
            river_side = int(river_prediction["side"])
            river_confidence = float(river_prediction["confidence"])
            challenger_side = int(challenger_prediction["side"])
            challenger_confidence = float(challenger_prediction["confidence"])
            label = int(realized)
        except (KeyError, TypeError, ValueError):
            continue
        if river_side not in {-1, 0, 1} or challenger_side not in {-1, 0, 1}:
            continue
        if label not in {-1, 0, 1}:
            continue

        river_sides.append(river_side)
        river_confidences.append(river_confidence)
        challenger_sides.append(challenger_side)
        challenger_confidences.append(challenger_confidence)
        labels.append(label)

    observations = len(labels)
    if observations == 0:
        empty = _empty_quality()
        return ShadowQualityComparison(
            observations=0,
            river=empty,
            challenger=empty,
        )

    index = pd.RangeIndex(observations)
    realized = pd.Series(labels, index=index, dtype="int64")
    river = evaluate_model_quality(
        pd.Series(river_sides, index=index, dtype="int64"),
        pd.Series(river_confidences, index=index, dtype="float64"),
        realized,
    )
    challenger = evaluate_model_quality(
        pd.Series(challenger_sides, index=index, dtype="int64"),
        pd.Series(challenger_confidences, index=index, dtype="float64"),
        realized,
    )
    return ShadowQualityComparison(
        observations=observations,
        river=river,
        challenger=challenger,
    )

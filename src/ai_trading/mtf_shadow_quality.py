from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any

import pandas as pd

from .model_quality import ModelQuality, evaluate_model_quality


@dataclass(frozen=True)
class MultiTimeframeShadowQuality:
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


def compare_mtf_shadow_audit_payloads(
    payloads: Iterable[dict[str, Any]],
) -> MultiTimeframeShadowQuality:
    """Compare delayed MTF predictions with River at the same execution time."""

    river_by_execution: dict[str, tuple[int, float]] = {}
    shadow_by_execution: dict[str, tuple[int, float, int]] = {}

    for payload in payloads:
        execution_time = payload.get("execution_time")
        prediction = payload.get("prediction")
        if isinstance(execution_time, str) and isinstance(prediction, dict):
            try:
                side = int(prediction["side"])
                confidence = float(prediction["confidence"])
            except (KeyError, TypeError, ValueError):
                pass
            else:
                if side in {-1, 0, 1}:
                    river_by_execution[execution_time] = (side, confidence)

        shadow = payload.get("mtf_shadow_challenger")
        if not isinstance(shadow, dict):
            continue
        shadow_execution = shadow.get("execution_time")
        shadow_prediction = shadow.get("prediction")
        realized = shadow.get("realized_label")
        if (
            not isinstance(shadow_execution, str)
            or not isinstance(shadow_prediction, dict)
            or realized is None
        ):
            continue
        try:
            side = int(shadow_prediction["side"])
            confidence = float(shadow_prediction["confidence"])
            label = int(realized)
        except (KeyError, TypeError, ValueError):
            continue
        if side not in {-1, 0, 1} or label not in {-1, 0, 1}:
            continue
        shadow_by_execution[shadow_execution] = (side, confidence, label)

    river_sides: list[int] = []
    river_confidences: list[float] = []
    challenger_sides: list[int] = []
    challenger_confidences: list[float] = []
    labels: list[int] = []

    for execution_time, challenger in shadow_by_execution.items():
        river = river_by_execution.get(execution_time)
        if river is None:
            continue
        river_side, river_confidence = river
        challenger_side, challenger_confidence, label = challenger
        river_sides.append(river_side)
        river_confidences.append(river_confidence)
        challenger_sides.append(challenger_side)
        challenger_confidences.append(challenger_confidence)
        labels.append(label)

    observations = len(labels)
    if observations == 0:
        empty = _empty_quality()
        return MultiTimeframeShadowQuality(
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
    return MultiTimeframeShadowQuality(
        observations=observations,
        river=river,
        challenger=challenger,
    )

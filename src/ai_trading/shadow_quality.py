from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .model import Prediction


@dataclass(frozen=True)
class ShadowObservation:
    signal_time: str
    execution_time: str
    regime: str
    realized_label: int
    active_prediction: Prediction
    challenger_prediction: Prediction


@dataclass(frozen=True)
class ShadowModelQuality:
    observations: int
    accuracy: float | None
    brier: float | None
    directional_edge: float | None
    directional_observations: int


@dataclass(frozen=True)
class ShadowQualityReport:
    observations: int
    agreement_rate: float | None
    active: ShadowModelQuality
    challenger: ShadowModelQuality
    accuracy_delta: float | None
    brier_improvement: float | None
    regimes: tuple[str, ...]


def _prediction_from_payload(payload: object) -> Prediction | None:
    if not isinstance(payload, dict):
        return None
    try:
        side = int(payload["side"])
        confidence = float(payload["confidence"])
        raw_probabilities = payload["probabilities"]
        if not isinstance(raw_probabilities, dict):
            return None
        probabilities = {
            side_key: float(raw_probabilities.get(str(side_key), raw_probabilities.get(side_key, 0.0)))
            for side_key in (-1, 0, 1)
        }
    except (KeyError, TypeError, ValueError):
        return None
    if side not in {-1, 0, 1}:
        return None
    return Prediction(
        side=side,
        confidence=confidence,
        probabilities=probabilities,
    )


def shadow_observation_from_audit_payload(
    payload: dict[str, Any],
) -> ShadowObservation | None:
    shadow = payload.get("shadow_challenger")
    if not isinstance(shadow, dict):
        return None

    active_prediction = _prediction_from_payload(payload.get("prediction"))
    challenger_prediction = _prediction_from_payload(shadow.get("prediction"))
    if active_prediction is None or challenger_prediction is None:
        return None

    realized = shadow.get("realized_label")
    if realized is None:
        return None
    try:
        realized_label = int(realized)
    except (TypeError, ValueError):
        return None
    if realized_label not in {-1, 0, 1}:
        return None

    signal_time = str(shadow.get("signal_time") or payload.get("signal_time") or "")
    execution_time = str(
        shadow.get("execution_time") or payload.get("execution_time") or ""
    )
    regime = str(shadow.get("regime") or payload.get("observed_regime") or "")
    if not signal_time or not execution_time:
        return None

    return ShadowObservation(
        signal_time=signal_time,
        execution_time=execution_time,
        regime=regime,
        realized_label=realized_label,
        active_prediction=active_prediction,
        challenger_prediction=challenger_prediction,
    )


def _model_quality(
    observations: tuple[ShadowObservation, ...],
    *,
    challenger: bool,
) -> ShadowModelQuality:
    if not observations:
        return ShadowModelQuality(
            observations=0,
            accuracy=None,
            brier=None,
            directional_edge=None,
            directional_observations=0,
        )

    predictions = [
        observation.challenger_prediction
        if challenger
        else observation.active_prediction
        for observation in observations
    ]
    correct = [
        int(prediction.side == observation.realized_label)
        for prediction, observation in zip(predictions, observations, strict=True)
    ]
    accuracy = sum(correct) / len(correct)

    classes = (-1, 0, 1)
    brier_values: list[float] = []
    for prediction, observation in zip(predictions, observations, strict=True):
        squared_error = sum(
            (
                float(prediction.probabilities.get(side, 0.0))
                - float(side == observation.realized_label)
            )
            ** 2
            for side in classes
        )
        brier_values.append(squared_error / len(classes))

    directional_pairs = [
        (prediction, observation)
        for prediction, observation in zip(predictions, observations, strict=True)
        if prediction.side != 0
    ]
    directional_observations = len(directional_pairs)
    directional_edge = None
    if directional_pairs:
        directional_accuracy = sum(
            prediction.side == observation.realized_label
            for prediction, observation in directional_pairs
        ) / directional_observations
        directional_edge = directional_accuracy - 0.5

    return ShadowModelQuality(
        observations=len(observations),
        accuracy=float(accuracy),
        brier=float(sum(brier_values) / len(brier_values)),
        directional_edge=(
            None if directional_edge is None else float(directional_edge)
        ),
        directional_observations=directional_observations,
    )


def evaluate_shadow_quality(
    observations: tuple[ShadowObservation, ...],
) -> ShadowQualityReport:
    active = _model_quality(observations, challenger=False)
    challenger = _model_quality(observations, challenger=True)
    if not observations:
        agreement_rate = None
        accuracy_delta = None
        brier_improvement = None
    else:
        agreement_rate = sum(
            observation.active_prediction.side
            == observation.challenger_prediction.side
            for observation in observations
        ) / len(observations)
        accuracy_delta = (
            None
            if active.accuracy is None or challenger.accuracy is None
            else challenger.accuracy - active.accuracy
        )
        brier_improvement = (
            None
            if active.brier is None or challenger.brier is None
            else active.brier - challenger.brier
        )

    return ShadowQualityReport(
        observations=len(observations),
        agreement_rate=(
            None if agreement_rate is None else float(agreement_rate)
        ),
        active=active,
        challenger=challenger,
        accuracy_delta=(
            None if accuracy_delta is None else float(accuracy_delta)
        ),
        brier_improvement=(
            None if brier_improvement is None else float(brier_improvement)
        ),
        regimes=tuple(
            sorted({observation.regime for observation in observations if observation.regime})
        ),
    )

from ai_trading.model import Prediction
from ai_trading.shadow_quality import (
    ShadowObservation,
    evaluate_shadow_quality,
    shadow_observation_from_audit_payload,
)


def prediction(
    side: int,
    probabilities: dict[int, float],
) -> Prediction:
    return Prediction(
        side=side,
        confidence=probabilities[side],
        probabilities=probabilities,
    )


def test_shadow_quality_compares_active_and_challenger_without_ranking() -> None:
    observations = (
        ShadowObservation(
            signal_time="t1",
            execution_time="e1",
            regime="bull_normal_vol",
            realized_label=1,
            active_prediction=prediction(1, {-1: 0.1, 0: 0.2, 1: 0.7}),
            challenger_prediction=prediction(1, {-1: 0.05, 0: 0.1, 1: 0.85}),
        ),
        ShadowObservation(
            signal_time="t2",
            execution_time="e2",
            regime="sideways_normal_vol",
            realized_label=0,
            active_prediction=prediction(1, {-1: 0.1, 0: 0.3, 1: 0.6}),
            challenger_prediction=prediction(0, {-1: 0.1, 0: 0.8, 1: 0.1}),
        ),
    )

    report = evaluate_shadow_quality(observations)

    assert report.observations == 2
    assert report.active.accuracy == 0.5
    assert report.challenger.accuracy == 1.0
    assert report.accuracy_delta == 0.5
    assert report.challenger.brier < report.active.brier
    assert report.brier_improvement > 0
    assert report.agreement_rate == 0.5
    assert report.active.directional_observations == 2
    assert report.active.directional_edge == 0.0
    assert report.challenger.directional_observations == 1
    assert report.challenger.directional_edge == 0.5
    assert report.regimes == ("bull_normal_vol", "sideways_normal_vol")


def test_empty_shadow_quality_has_no_false_precision() -> None:
    report = evaluate_shadow_quality(())

    assert report.observations == 0
    assert report.agreement_rate is None
    assert report.active.accuracy is None
    assert report.active.brier is None
    assert report.challenger.accuracy is None
    assert report.challenger.brier is None
    assert report.accuracy_delta is None
    assert report.brier_improvement is None
    assert report.regimes == ()


def test_shadow_observation_parses_json_string_probability_keys() -> None:
    payload = {
        "signal_time": "2026-09-19 10:00:00+00:00",
        "execution_time": "2026-09-19 10:05:00+00:00",
        "observed_regime": "bull_normal_vol",
        "prediction": {
            "side": 1,
            "confidence": 0.7,
            "probabilities": {"-1": 0.1, "0": 0.2, "1": 0.7},
        },
        "shadow_challenger": {
            "signal_time": "2026-09-19 10:00:00+00:00",
            "execution_time": "2026-09-19 10:05:00+00:00",
            "regime": "bull_normal_vol",
            "training_rows": 150,
            "training_end": "2026-09-19 09:55:00+00:00",
            "realized_label": 1,
            "prediction": {
                "side": 0,
                "confidence": 0.6,
                "probabilities": {"-1": 0.1, "0": 0.6, "1": 0.3},
            },
        },
    }

    observation = shadow_observation_from_audit_payload(payload)

    assert observation is not None
    assert observation.realized_label == 1
    assert observation.active_prediction.side == 1
    assert observation.active_prediction.probabilities[1] == 0.7
    assert observation.challenger_prediction.side == 0
    assert observation.regime == "bull_normal_vol"


def test_shadow_observation_ignores_missing_realized_label() -> None:
    payload = {
        "prediction": {
            "side": 0,
            "confidence": 1.0,
            "probabilities": {"-1": 0.0, "0": 1.0, "1": 0.0},
        },
        "shadow_challenger": {
            "realized_label": None,
            "prediction": {
                "side": 0,
                "confidence": 1.0,
                "probabilities": {"-1": 0.0, "0": 1.0, "1": 0.0},
            },
        },
    }

    assert shadow_observation_from_audit_payload(payload) is None

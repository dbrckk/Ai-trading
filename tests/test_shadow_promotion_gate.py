from ai_trading.model_quality import ModelQuality
from ai_trading.shadow_promotion_gate import (
    ShadowPromotionPolicy,
    evaluate_shadow_promotion_gate,
)
from ai_trading.shadow_quality import ShadowQualityComparison


def comparison(
    *,
    observations: int,
    river_score: float = 0.60,
    challenger_score: float = 0.64,
    river_accuracy: float = 0.55,
    challenger_accuracy: float = 0.57,
    river_brier: float = 0.30,
    challenger_brier: float = 0.28,
    river_edge: float = 0.05,
    challenger_edge: float = 0.08,
    directional_labels: int | None = None,
    directional_predictions: int | None = None,
) -> ShadowQualityComparison:
    river = ModelQuality(
        score=river_score,
        accuracy=river_accuracy,
        brier=river_brier,
        directional_edge=river_edge,
        observations=observations,
    )
    challenger = ModelQuality(
        score=challenger_score,
        accuracy=challenger_accuracy,
        brier=challenger_brier,
        directional_edge=challenger_edge,
        observations=observations,
    )
    return ShadowQualityComparison(
        observations=observations,
        river=river,
        challenger=challenger,
        directional_labels=(
            int(observations * 0.60)
            if directional_labels is None
            else directional_labels
        ),
        directional_predictions=(
            int(observations * 0.40)
            if directional_predictions is None
            else directional_predictions
        ),
    )


def test_shadow_promotion_gate_requires_sufficient_evidence() -> None:
    gate = evaluate_shadow_promotion_gate(comparison(observations=40))

    assert gate.eligible_for_review is False
    assert any("250" in reason for reason in gate.reasons)


def test_shadow_promotion_gate_accepts_stronger_challenger_for_review() -> None:
    gate = evaluate_shadow_promotion_gate(comparison(observations=300))

    assert gate.eligible_for_review is True
    assert gate.reasons == ()
    assert gate.score_delta > 0.0
    assert gate.accuracy_delta > 0.0
    assert gate.brier_delta < 0.0
    assert gate.directional_edge_delta > 0.0
    assert gate.directional_observations >= 100
    assert gate.directional_predictions >= 50


def test_shadow_promotion_gate_rejects_calibration_degradation() -> None:
    gate = evaluate_shadow_promotion_gate(
        comparison(
            observations=300,
            challenger_score=0.66,
            challenger_accuracy=0.60,
            challenger_brier=0.35,
            challenger_edge=0.10,
        ),
        ShadowPromotionPolicy(max_brier_increase=0.02),
    )

    assert gate.eligible_for_review is False
    assert "calibration error degraded beyond tolerance" in gate.reasons

    # High aggregate accuracy alone must not qualify an all-flat model.
    flat = evaluate_shadow_promotion_gate(
        comparison(
            observations=500,
            challenger_score=0.95,
            challenger_accuracy=0.98,
            challenger_brier=0.03,
            challenger_edge=0.12,
            directional_labels=150,
            directional_predictions=0,
        )
    )
    assert flat.eligible_for_review is False
    assert flat.directional_predictions == 0
    assert any("50 confident" in reason for reason in flat.reasons)

    # A market with mostly flat realized labels cannot establish
    # a meaningful directional trading edge, even at 500 samples.
    missing_directional_labels = evaluate_shadow_promotion_gate(
        comparison(
            observations=500,
            directional_labels=20,
            directional_predictions=120,
        )
    )
    assert missing_directional_labels.eligible_for_review is False
    assert any("100 realized directional" in r for r in missing_directional_labels.reasons)

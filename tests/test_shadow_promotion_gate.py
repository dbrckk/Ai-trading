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

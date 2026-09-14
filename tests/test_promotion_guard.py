from ai_trading.promotion_guard import PromotionPolicy, evaluate_promotion

BASELINE = {
    "sharpe": 1.0,
    "sortino": 1.2,
    "max_drawdown": 0.10,
    "calmar": 1.1,
}


def test_promotion_guard_accepts_better_challenger() -> None:
    decision = evaluate_promotion(
        champion_score=1.0,
        champion_metrics=BASELINE,
        challenger_score=1.1,
        challenger_metrics={
            "sharpe": 1.1,
            "sortino": 1.3,
            "max_drawdown": 0.09,
            "calmar": 1.2,
        },
    )
    assert decision.approved
    assert not decision.reasons


def test_promotion_guard_rejects_drawdown_regression() -> None:
    decision = evaluate_promotion(
        champion_score=1.0,
        champion_metrics=BASELINE,
        challenger_score=1.2,
        challenger_metrics={
            "sharpe": 1.2,
            "sortino": 1.4,
            "max_drawdown": 0.14,
            "calmar": 1.2,
        },
    )
    assert not decision.approved
    assert "max drawdown degradation exceeds policy" in decision.reasons


def test_promotion_guard_is_fail_closed_on_missing_metric() -> None:
    decision = evaluate_promotion(
        champion_score=1.0,
        champion_metrics=BASELINE,
        challenger_score=1.2,
        challenger_metrics={
            "sharpe": 1.2,
            "sortino": 1.4,
            "max_drawdown": 0.09,
        },
    )
    assert not decision.approved
    assert "missing required metrics" in decision.reasons[0]


def test_promotion_policy_can_require_strict_score_gain() -> None:
    decision = evaluate_promotion(
        champion_score=1.0,
        champion_metrics=BASELINE,
        challenger_score=1.01,
        challenger_metrics=BASELINE,
        policy=PromotionPolicy(min_score_improvement=0.05),
    )
    assert not decision.approved

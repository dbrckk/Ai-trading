from ai_trading.economic_meta import EconomicMetaStats
from ai_trading.expert_lifecycle import ExpertLifecyclePolicy, evaluate_expert_lifecycle


def test_expert_lifecycle_retires_persistently_bad_expert() -> None:
    stats = EconomicMetaStats(score=-0.05, observations=30)
    decision = evaluate_expert_lifecycle(stats)
    assert decision.action == "retire"


def test_expert_lifecycle_retrains_mildly_degraded_expert() -> None:
    stats = EconomicMetaStats(score=-0.01, observations=30)
    decision = evaluate_expert_lifecycle(
        stats,
        ExpertLifecyclePolicy(
            min_observations=20,
            retire_below_score=-0.03,
            retrain_below_score=-0.005,
        ),
    )
    assert decision.action == "retrain"


def test_expert_lifecycle_keeps_early_expert() -> None:
    stats = EconomicMetaStats(score=-1.0, observations=3)
    decision = evaluate_expert_lifecycle(stats)
    assert decision.action == "keep"

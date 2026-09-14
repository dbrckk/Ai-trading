from ai_trading.expert_pool import (
    ExpertPoolPolicy,
    ExpertRecord,
    compute_budget_weights,
    reconcile_pool,
)


def test_pool_promotes_best_validated_challenger_and_caps_active() -> None:
    records = {
        "a": ExpertRecord("a", "trend", "challenger", score=0.8, validation_score=0.8),
        "b": ExpertRecord("b", "range", "challenger", score=0.7, validation_score=0.7),
        "c": ExpertRecord("c", "high_vol", "challenger", score=0.6, validation_score=0.6),
    }
    reconciled = reconcile_pool(
        records,
        ExpertPoolPolicy(max_active_experts=2, min_promotion_score=0.55),
    )
    assert sum(r.status == "active" for r in reconciled.values()) == 2


def test_pool_prunes_persistently_bad_expert() -> None:
    records = {
        "bad": ExpertRecord(
            "bad",
            "trend",
            "active",
            score=0.10,
            validation_score=0.7,
            observations=50,
        )
    }
    reconciled = reconcile_pool(records)
    assert reconciled["bad"].status == "pruned"


def test_compute_budget_rewards_quality_per_compute_cost() -> None:
    records = {
        "efficient": ExpertRecord("efficient", "trend", "active", score=0.8, compute_cost=1.0),
        "expensive": ExpertRecord("expensive", "range", "active", score=0.8, compute_cost=4.0),
    }
    weights = compute_budget_weights(records)
    assert weights["efficient"] > weights["expensive"]
    assert abs(sum(weights.values()) - 1.0) < 1e-9

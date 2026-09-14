from ai_trading.compute_budget import ComputeBudget, allocate_compute_budget
from ai_trading.expert_pool import ExpertRecord


def test_compute_budget_sums_to_total_and_rewards_efficiency() -> None:
    records = {
        "fast": ExpertRecord("fast", "trend", "active", score=0.8, compute_cost=1.0),
        "slow": ExpertRecord("slow", "range", "active", score=0.8, compute_cost=4.0),
    }
    allocation = allocate_compute_budget(
        records,
        ComputeBudget(total_units=100.0, exploration_fraction=0.10),
    )
    assert abs(sum(allocation.values()) - 100.0) < 1e-9
    assert allocation["fast"] > allocation["slow"]

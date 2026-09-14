from pathlib import Path

from ai_trading.crisis_controller import (
    CrisisPolicy,
    CrisisState,
    evaluate_crisis_state,
    limits_for_state,
)
from ai_trading.crisis_state_store import CrisisStateStore


def test_crisis_escalates_immediately_and_recovers_with_hysteresis() -> None:
    policy = CrisisPolicy(recovery_confirmations=2)
    decision = evaluate_crisis_state(
        CrisisState(),
        stress_scale=0.25,
        drawdown=0.02,
        policy=policy,
    )
    assert decision.state.mode == "capital-preservation"
    assert decision.exposure_scale == 0.10

    hold = evaluate_crisis_state(
        decision.state,
        stress_scale=1.0,
        drawdown=0.0,
        policy=policy,
    )
    assert hold.state.mode == "capital-preservation"
    assert hold.state.recovery_streak == 1

    recover = evaluate_crisis_state(
        hold.state,
        stress_scale=1.0,
        drawdown=0.0,
        policy=policy,
    )
    assert recover.state.mode == "defensive"


def test_crisis_state_store_round_trip(tmp_path: Path) -> None:
    store = CrisisStateStore(tmp_path / "crisis.json")
    state = CrisisState(mode="defensive", recovery_streak=1)
    store.save(state)
    assert store.load() == state
    assert limits_for_state(state).max_active_experts == 3

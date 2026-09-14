from pathlib import Path

from ai_trading.resilience import (
    ResiliencePolicy,
    ResilienceSignals,
    ResilienceState,
    ResilienceStateStore,
    evaluate_resilience,
)


def signals(**overrides) -> ResilienceSignals:
    values = {
        "governor_verdict": "TRADE",
        "crisis_mode": "normal",
        "recovery_degraded": False,
        "recovery_recent_failures": 0,
        "recovery_fallback_depth": 0,
    }
    values.update(overrides)
    return ResilienceSignals(**values)


def test_resilience_escalates_to_degraded() -> None:
    decision = evaluate_resilience(
        ResilienceState(),
        signals(recovery_degraded=True),
    )

    assert decision.state.mode == "DEGRADED"
    assert decision.exposure_cap == 0.35
    assert not decision.promotions_allowed
    assert decision.scheduler_allowed


def test_resilience_enters_halt_on_critical_recovery_failure() -> None:
    decision = evaluate_resilience(
        ResilienceState(),
        signals(recovery_recent_failures=4),
    )

    assert decision.state.mode == "HALT"
    assert decision.exposure_cap == 0.0
    assert not decision.scheduler_allowed


def test_resilience_requires_recovery_confirmations() -> None:
    policy = ResiliencePolicy(recovery_confirmations=2)
    first = evaluate_resilience(
        ResilienceState(mode="DEGRADED"),
        signals(),
        policy,
    )
    second = evaluate_resilience(first.state, signals(), policy)

    assert first.state.mode == "RECOVERY"
    assert second.state.mode == "NORMAL"


def test_halt_requires_cooldown_before_normal() -> None:
    policy = ResiliencePolicy(cooldown_confirmations=2)
    first = evaluate_resilience(
        ResilienceState(mode="HALT"),
        signals(),
        policy,
    )
    second = evaluate_resilience(first.state, signals(), policy)

    assert first.state.mode == "COOLDOWN"
    assert second.state.mode == "NORMAL"


def test_resilience_store_persists_state(tmp_path: Path) -> None:
    store = ResilienceStateStore(tmp_path / "resilience.json")
    state = ResilienceState(mode="CAUTIOUS", healthy_streak=1, reason="test")

    store.save(state)

    assert store.load() == state

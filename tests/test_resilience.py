from pathlib import Path

from ai_trading.resilience import (
    ResilienceContext,
    ResiliencePolicy,
    ResilienceSignals,
    ResilienceState,
    ResilienceStateStore,
    adapt_resilience_policy,
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



def test_adaptive_policy_never_increases_nominal_exposure() -> None:
    base = ResiliencePolicy()
    adaptive = adapt_resilience_policy(
        base,
        ResilienceContext(
            data_quality=0.80,
            drawdown=0.13,
            annualized_volatility=0.55,
            recent_incidents=5,
        ),
    )

    assert adaptive.cautious_exposure_cap <= base.cautious_exposure_cap
    assert adaptive.degraded_exposure_cap <= base.degraded_exposure_cap
    assert adaptive.recovery_exposure_cap <= base.recovery_exposure_cap
    assert adaptive.cooldown_exposure_cap <= base.cooldown_exposure_cap
    assert adaptive.halt_recovery_failures <= base.halt_recovery_failures
    assert adaptive.halt_recovery_fallback_depth <= base.halt_recovery_fallback_depth
    assert adaptive.recovery_confirmations >= base.recovery_confirmations


def test_adaptive_policy_is_unchanged_in_healthy_conditions() -> None:
    base = ResiliencePolicy()
    adaptive = adapt_resilience_policy(
        base,
        ResilienceContext(
            data_quality=1.0,
            drawdown=0.01,
            annualized_volatility=0.15,
            recent_incidents=0,
        ),
    )

    assert adaptive == base


def test_adaptive_policy_tightens_degraded_exposure() -> None:
    base = ResiliencePolicy()
    adaptive = adapt_resilience_policy(
        base,
        ResilienceContext(
            data_quality=0.90,
            drawdown=0.09,
            annualized_volatility=0.35,
            recent_incidents=2,
        ),
    )
    decision = evaluate_resilience(
        ResilienceState(),
        signals(recovery_degraded=True),
        adaptive,
    )

    assert decision.state.mode == "DEGRADED"
    assert decision.exposure_cap < base.degraded_exposure_cap



def test_resilience_store_loads_legacy_state_without_instability_field(
    tmp_path: Path,
) -> None:
    path = tmp_path / "resilience.json"
    path.write_text(
        '{"healthy_streak":2,"mode":"RECOVERY","mode_steps":3,"reason":"legacy"}',
        encoding="utf-8",
    )

    state = ResilienceStateStore(path).load()

    assert state.mode == "RECOVERY"
    assert state.mode_steps == 3
    assert state.instability_status == "stable"

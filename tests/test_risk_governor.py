from ai_trading.risk_governor import GovernorSignals, evaluate_governor


def base_signals(**overrides):
    values = {
        "data_quality": 1.0,
        "system_healthy": True,
        "model_confidence": 0.8,
        "portfolio_risk_approved": True,
        "stress_approved": True,
        "stressed_cvar": 0.02,
        "drawdown": 0.01,
        "crisis_mode": "normal",
        "liquidity_stressed": False,
        "recovery_degraded": False,
        "recovery_recent_failures": 0,
        "recovery_fallback_depth": 0,
    }
    values.update(overrides)
    return GovernorSignals(**values)


def test_governor_trade_when_all_gates_pass() -> None:
    decision = evaluate_governor(base_signals())
    assert decision.verdict == "TRADE"


def test_governor_reduces_on_elevated_risk() -> None:
    decision = evaluate_governor(base_signals(crisis_mode="cautious"))
    assert decision.verdict == "REDUCE"
    assert decision.exposure_scale == 0.50


def test_governor_freezes_on_failed_risk_gate() -> None:
    decision = evaluate_governor(base_signals(portfolio_risk_approved=False))
    assert decision.verdict == "FREEZE"
    assert not decision.allow_rebalance


def test_governor_flattens_on_extreme_drawdown() -> None:
    decision = evaluate_governor(base_signals(drawdown=0.20))
    assert decision.verdict == "FLATTEN"
    assert decision.flatten


def test_governor_halts_on_critical_data_failure() -> None:
    decision = evaluate_governor(base_signals(data_quality=0.50))
    assert decision.verdict == "HALT"
    assert decision.halt


def test_failed_stress_test_reduces_instead_of_freezing() -> None:
    decision = evaluate_governor(
        base_signals(
            stress_approved=False,
            stressed_cvar=0.04,
        )
    )
    assert decision.verdict == "REDUCE"
    assert decision.allow_rebalance



def test_governor_reduces_when_recovery_health_is_degraded() -> None:
    decision = evaluate_governor(
        base_signals(
            recovery_degraded=True,
            recovery_recent_failures=1,
            recovery_fallback_depth=2,
        )
    )
    assert decision.verdict == "REDUCE"
    assert decision.exposure_scale == 0.35
    assert decision.reason == "recovery health degraded"


def test_governor_halts_after_repeated_recovery_failures() -> None:
    decision = evaluate_governor(
        base_signals(
            recovery_degraded=True,
            recovery_recent_failures=4,
            recovery_fallback_depth=1,
        )
    )
    assert decision.verdict == "HALT"
    assert decision.halt


def test_governor_halts_on_excessive_recovery_fallback_depth() -> None:
    decision = evaluate_governor(
        base_signals(
            recovery_degraded=True,
            recovery_recent_failures=0,
            recovery_fallback_depth=5,
        )
    )
    assert decision.verdict == "HALT"
    assert decision.halt


def test_governor_returns_to_trade_after_recovery_health_normalizes() -> None:
    degraded = evaluate_governor(base_signals(recovery_degraded=True))
    healthy = evaluate_governor(base_signals(recovery_degraded=False))

    assert degraded.verdict == "REDUCE"
    assert healthy.verdict == "TRADE"

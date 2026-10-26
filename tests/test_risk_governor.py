import math

import pytest

from ai_trading.risk_governor import GovernorPolicy, GovernorSignals, evaluate_governor


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


@pytest.mark.parametrize(
    "field,value",
    [
        ("data_quality", math.nan),
        ("data_quality", math.inf),
        ("model_confidence", math.nan),
        ("model_confidence", 1.5),
        ("stressed_cvar", math.nan),
        ("stressed_cvar", -0.1),
        ("drawdown", math.nan),
        ("drawdown", -0.1),
        ("recovery_recent_failures", math.nan),
        ("recovery_fallback_depth", math.inf),
        ("data_quality", "healthy"),
        ("model_confidence", True),
        ("stressed_cvar", None),
        ("drawdown", "0.01"),
        ("recovery_recent_failures", 1.5),
        ("recovery_recent_failures", True),
        ("recovery_fallback_depth", "0"),
    ],
)
def test_governor_halts_on_invalid_numeric_risk_evidence(
    field: str, value: float
) -> None:
    decision = evaluate_governor(base_signals(**{field: value}))

    assert decision.verdict == "HALT"
    assert decision.halt is True
    assert decision.allow_rebalance is False
    assert decision.exposure_scale == 0.0
    assert decision.reason == "invalid risk governor signal"


@pytest.mark.parametrize(
    "field,value",
    [
        ("min_data_quality", math.nan),
        ("halt_data_quality", math.inf),
        ("min_model_confidence", -0.1),
        ("flatten_drawdown", 1.1),
        ("reduce_stressed_cvar", math.nan),
        ("degraded_recovery_exposure_scale", 0.0),
        ("halt_recovery_failures", 0),
        ("halt_recovery_fallback_depth", 2.5),
        ("halt_recovery_failures", True),
    ],
)
def test_governor_rejects_unsafe_policy_config(field, value) -> None:
    with pytest.raises(ValueError):
        GovernorPolicy(**{field: value})


@pytest.mark.parametrize(
    "overrides",
    [
        {"halt_data_quality": 0.96, "min_data_quality": 0.95},
        {"reduce_drawdown": 0.20, "flatten_drawdown": 0.15},
        {"reduce_stressed_cvar": 0.10, "max_stressed_cvar": 0.08},
    ],
)
def test_governor_policy_rejects_reversed_risk_thresholds(overrides) -> None:
    with pytest.raises(ValueError):
        GovernorPolicy(**overrides)


def test_valid_governor_policy_keeps_default_trade_behavior() -> None:
    decision = evaluate_governor(base_signals(), GovernorPolicy())
    assert decision.verdict == "TRADE"


@pytest.mark.parametrize(
    "field,value",
    [
        ("system_healthy", "yes"),
        ("portfolio_risk_approved", 1),
        ("stress_approved", None),
        ("liquidity_stressed", "false"),
        ("recovery_degraded", 0),
        ("crisis_mode", None),
    ],
)
def test_governor_halts_on_malformed_boolean_or_mode_telemetry(field, value) -> None:
    decision = evaluate_governor(base_signals(**{field: value}))
    assert decision.verdict == "HALT"
    assert decision.halt is True
    assert decision.allow_rebalance is False
    assert decision.exposure_scale == 0.0

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

from ai_trading.soak import SoakResult
from ai_trading.soak_gate import evaluate_soak_qualification


def test_soak_gate_rejects_excessive_drawdown() -> None:
    result = SoakResult(
        cycles=100,
        successes=100,
        failures=0,
        final_equity=95000.0,
        governor_verdict="TRADE",
        crisis_mode="normal",
        errors=(),
        max_drawdown=0.20,
        min_equity=80000.0,
    )
    qualification = evaluate_soak_qualification(result)
    assert not qualification.passed
    assert "soak drawdown exceeded threshold" in qualification.reasons

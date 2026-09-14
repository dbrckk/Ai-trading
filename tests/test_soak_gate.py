from ai_trading.soak import SoakResult
from ai_trading.soak_gate import (
    SoakQualificationPolicy,
    evaluate_soak_qualification,
)


def test_soak_gate_passes_stable_run() -> None:
    result = SoakResult(
        cycles=100,
        successes=100,
        failures=0,
        final_equity=101000.0,
        governor_verdict="TRADE",
        crisis_mode="normal",
        errors=(),
    )
    qualification = evaluate_soak_qualification(result)
    assert qualification.passed


def test_soak_gate_rejects_halted_run() -> None:
    result = SoakResult(
        cycles=100,
        successes=99,
        failures=1,
        final_equity=99000.0,
        governor_verdict="HALT",
        crisis_mode="defensive",
        errors=("x",),
    )
    qualification = evaluate_soak_qualification(
        result,
        SoakQualificationPolicy(min_cycles=50),
    )
    assert not qualification.passed

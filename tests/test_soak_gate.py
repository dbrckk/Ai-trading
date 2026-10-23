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


def test_soak_gate_rejects_invalid_numerical_evidence() -> None:
    from dataclasses import replace
    import math

    valid = SoakResult(
        cycles=100,
        successes=100,
        failures=0,
        final_equity=101000.0,
        governor_verdict="TRADE",
        crisis_mode="normal",
        errors=(),
        max_drawdown=0.02,
        duration_seconds=3600.0,
    )
    for field, invalid in (
        ("max_drawdown", math.nan),
        ("max_drawdown", -0.01),
        ("duration_seconds", math.inf),
        ("duration_seconds", -1.0),
        ("final_equity", math.nan),
        ("final_equity", None),
        ("min_equity", math.inf),
    ):
        report = evaluate_soak_qualification(replace(valid, **{field: invalid}))
        assert not report.passed, field
        assert any(reason.startswith("invalid soak") for reason in report.reasons)


def test_soak_gate_rejects_inconsistent_cycle_counts() -> None:
    result = SoakResult(
        cycles=100,
        successes=101,
        failures=0,
        final_equity=101000.0,
        governor_verdict="TRADE",
        crisis_mode="normal",
        errors=(),
    )
    report = evaluate_soak_qualification(result)
    assert not report.passed
    assert "inconsistent soak cycle counts" in report.reasons


def test_soak_policy_rejects_nonfinite_thresholds() -> None:
    import math
    import pytest

    with pytest.raises(ValueError, match="min_success_ratio"):
        SoakQualificationPolicy(min_success_ratio=math.nan)
    with pytest.raises(ValueError, match="max_drawdown"):
        SoakQualificationPolicy(max_drawdown=math.inf)

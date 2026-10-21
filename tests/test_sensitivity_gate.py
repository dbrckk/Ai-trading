from dataclasses import replace

from ai_trading.parameter_sensitivity import SensitivityResult, SensitivityScenario
from ai_trading.sensitivity_gate import evaluate_sensitivity_gate


def result(
    name: str,
    *,
    excess: float = 0.02,
    sharpe: float = 0.8,
    drawdown: float = 0.15,
) -> SensitivityResult:
    return SensitivityResult(
        scenario=SensitivityScenario(name),
        total_return=0.10,
        excess_return=excess,
        sharpe=sharpe,
        max_drawdown=drawdown,
        trades=30,
    )


def test_sensitivity_gate_accepts_stable_neighborhood() -> None:
    results = tuple(result(f"s{i}") for i in range(6))

    gate = evaluate_sensitivity_gate(results)

    assert gate.passed
    assert gate.pass_ratio == 1.0
    assert gate.passing_scenarios == 6


def test_sensitivity_gate_rejects_narrow_optimum() -> None:
    results = (
        result("a"),
        result("b"),
        result("c", excess=-0.20),
        result("d", sharpe=-0.5),
        result("e", drawdown=0.45),
        result("f", excess=-0.15),
    )

    gate = evaluate_sensitivity_gate(results)

    assert not gate.passed
    assert gate.pass_ratio < 0.67

    # These used to pass the gate despite losing money, missing trades,
    # or emitting invalid/non-physical research measurements.
    losses = tuple(
        replace(result(f"loss{i}", excess=0.15), total_return=-0.02)
        for i in range(6)
    )
    loss_gate = evaluate_sensitivity_gate(losses)
    assert loss_gate.passed is False
    assert loss_gate.passing_scenarios == 0
    assert "no sensitivity scenario has positive net return" in loss_gate.reasons

    for invalid in (
        replace(result("invalid"), total_return=float("nan")),
        replace(result("invalid"), sharpe=float("inf")),
        replace(result("invalid"), trades=0),
        replace(result("invalid"), max_drawdown=-0.01),
        replace(result("invalid"), total_return=0.0),
    ):
        candidates = tuple(invalid for _ in range(6))
        decision = evaluate_sensitivity_gate(candidates)
        assert decision.passed is False
        assert decision.passing_scenarios == 0

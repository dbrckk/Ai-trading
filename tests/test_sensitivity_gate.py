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


def test_sensitivity_gate_rejects_losses_despite_positive_benchmark_excess() -> None:
    scenarios = tuple(
        replace(result(f"s{i}", excess=0.12), total_return=-0.01)
        for i in range(6)
    )
    gate = evaluate_sensitivity_gate(scenarios)

    assert gate.passed is False
    assert gate.passing_scenarios == 0
    assert "no sensitivity scenario has positive net return" in gate.reasons


def test_sensitivity_gate_rejects_invalid_and_nontrading_scenarios() -> None:
    scenarios = (
        replace(result("nan"), total_return=float("nan")),
        replace(result("infinite"), sharpe=float("inf")),
        replace(result("no_trades"), trades=0),
        replace(result("invalid_drawdown"), max_drawdown=-0.1),
    )
    gate = evaluate_sensitivity_gate(scenarios)

    assert gate.passed is False
    assert gate.passing_scenarios == 0
    assert gate.scenarios == 4


def test_sensitivity_gate_requires_profitable_majority() -> None:
    scenarios = (
        result("a"),
        result("b"),
        result("c"),
        replace(result("d"), total_return=-0.02),
        replace(result("e"), total_return=-0.01),
        replace(result("f"), total_return=-0.03),
    )
    gate = evaluate_sensitivity_gate(scenarios)

    assert gate.passed is False
    assert gate.passing_scenarios == 3
    assert gate.pass_ratio == 0.5

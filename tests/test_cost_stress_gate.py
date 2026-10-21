from dataclasses import replace

from ai_trading.cost_stress import CostStressResult, CostStressScenario
from ai_trading.cost_stress_gate import evaluate_cost_stress_gate


def result(
    name: str,
    *,
    excess: float = 0.02,
    sharpe: float = 0.8,
    drawdown: float = 0.15,
) -> CostStressResult:
    return CostStressResult(
        scenario=CostStressScenario(name, 1.0, 2.0),
        total_return=0.10,
        excess_return=excess,
        sharpe=sharpe,
        max_drawdown=drawdown,
        trades=30,
    )


def test_cost_stress_gate_accepts_resilient_strategy() -> None:
    gate = evaluate_cost_stress_gate(
        (result("base"), result("elevated"), result("severe"))
    )

    assert gate.passed
    assert gate.pass_ratio == 1.0


def test_cost_stress_gate_rejects_cost_fragility() -> None:
    gate = evaluate_cost_stress_gate(
        (
            result("base"),
            result("elevated", excess=-0.10),
            result("severe", sharpe=-0.5, drawdown=0.40),
        )
    )

    assert not gate.passed
    assert gate.pass_ratio < 0.67


def test_cost_stress_gate_rejects_negative_net_returns_despite_positive_excess() -> None:
    """Beating a falling benchmark is not equivalent to making money."""
    scenarios = tuple(
        replace(result(name, excess=0.10, sharpe=0.3), total_return=-0.01)
        for name in ("base", "elevated", "severe")
    )
    gate = evaluate_cost_stress_gate(scenarios)

    assert gate.passed is False
    assert gate.passing_scenarios == 0
    assert "no cost-stress scenario has positive net return" in gate.reasons


def test_cost_stress_gate_rejects_invalid_or_zero_trade_evidence() -> None:
    scenarios = (
        replace(result("base"), total_return=float("nan")),
        replace(result("elevated"), sharpe=float("inf")),
        replace(result("severe"), trades=0),
    )
    gate = evaluate_cost_stress_gate(scenarios)

    assert gate.passed is False
    assert gate.passing_scenarios == 0
    assert gate.scenarios == 3


def test_cost_stress_gate_counts_only_profitable_cost_scenarios() -> None:
    scenarios = (
        result("base"),
        result("elevated"),
        replace(result("severe"), total_return=-0.03),
    )
    gate = evaluate_cost_stress_gate(scenarios)

    assert gate.passed is False
    assert gate.passing_scenarios == 2
    assert gate.pass_ratio == 2 / 3

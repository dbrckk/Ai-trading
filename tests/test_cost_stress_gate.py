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

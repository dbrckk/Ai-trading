from ai_trading.bootstrap_gate import BootstrapGatePolicy, evaluate_bootstrap_gate
from ai_trading.bootstrap_robustness import BootstrapReport


def report(
    *,
    positive: float = 0.75,
    loss: float = 0.25,
    lower: float = -0.08,
    drawdown: float = 0.20,
) -> BootstrapReport:
    return BootstrapReport(
        simulations=2000,
        probability_positive=positive,
        probability_loss=loss,
        median_return=0.10,
        lower_return=lower,
        upper_return=0.30,
        median_max_drawdown=0.10,
        upper_max_drawdown=drawdown,
    )


def test_bootstrap_gate_accepts_robust_distribution() -> None:
    result = evaluate_bootstrap_gate(report())

    assert result.passed


def test_bootstrap_gate_rejects_fragile_distribution() -> None:
    result = evaluate_bootstrap_gate(
        report(positive=0.40, loss=0.60, lower=-0.30, drawdown=0.45),
        BootstrapGatePolicy(),
    )

    assert not result.passed
    assert len(result.reasons) == 4

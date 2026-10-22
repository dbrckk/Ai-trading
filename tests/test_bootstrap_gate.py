from dataclasses import replace

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

    # The research gate must fail closed on malformed bootstrap evidence.
    invalid_cases = (
        (
            replace(report(), probability_positive=float("nan")),
            "non-finite bootstrap distribution",
        ),
        (
            replace(report(), probability_loss=float("inf")),
            "non-finite bootstrap distribution",
        ),
        (replace(report(), probability_positive=1.1), "incoherent bootstrap distribution"),
        (
            replace(report(), probability_positive=0.8, probability_loss=0.5),
            "incoherent bootstrap distribution",
        ),
        (replace(report(), lower_return=0.2), "incoherent bootstrap distribution"),
        (
            replace(report(), upper_max_drawdown=-0.1),
            "incoherent bootstrap distribution",
        ),
        (replace(report(), simulations=0), "insufficient bootstrap simulations"),
    )
    for invalid, expected_reason in invalid_cases:
        decision = evaluate_bootstrap_gate(invalid)
        assert decision.passed is False
        assert expected_reason in decision.reasons

from types import SimpleNamespace

from ai_trading.quantitative_qualification import (
    evaluate_quantitative_qualification,
)


def gate(passed: bool, *reasons: str):
    return SimpleNamespace(passed=passed, reasons=tuple(reasons))


def test_quantitative_qualification_requires_all_gates() -> None:
    result = evaluate_quantitative_qualification(
        benchmark=gate(True),
        regime=gate(True),
        bootstrap=gate(True),
        sensitivity=gate(True),
    )

    assert result.qualified
    assert result.passed_gates == 4
    assert result.total_gates == 4


def test_quantitative_qualification_aggregates_rejections() -> None:
    result = evaluate_quantitative_qualification(
        benchmark=gate(False, "Sharpe below threshold"),
        regime=gate(True),
        bootstrap=gate(False, "drawdown tail above threshold"),
        sensitivity=gate(True),
    )

    assert not result.qualified
    assert result.passed_gates == 2
    assert "benchmark: Sharpe below threshold" in result.reasons
    assert "bootstrap: drawdown tail above threshold" in result.reasons

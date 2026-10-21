from dataclasses import replace
from types import SimpleNamespace

from ai_trading.benchmark_gate import BenchmarkGatePolicy, evaluate_benchmark_gate
from ai_trading.performance import PerformanceMetrics


def _report(
    *,
    sharpe: float = 1.0,
    sortino: float = 1.2,
    calmar: float = 1.0,
    drawdown: float = 0.10,
    excess: float = 0.05,
    folds: int = 6,
    trades: int = 40,
) -> SimpleNamespace:
    metrics = PerformanceMetrics(
        total_return=0.20,
        annualized_return=0.10,
        annualized_volatility=0.10,
        sharpe=sharpe,
        sortino=sortino,
        max_drawdown=drawdown,
        calmar=calmar,
    )
    return SimpleNamespace(
        metrics=metrics,
        excess_return=excess,
        folds=folds,
        trades=trades,
    )


def test_benchmark_gate_accepts_qualified_report() -> None:
    result = evaluate_benchmark_gate(_report())

    assert result.passed
    assert result.reasons == ()


def test_benchmark_gate_rejects_weak_out_of_sample_result() -> None:
    result = evaluate_benchmark_gate(
        _report(sharpe=0.1, drawdown=0.35, excess=-0.03, trades=5),
        BenchmarkGatePolicy(),
    )

    assert not result.passed
    assert "Sharpe below threshold" in result.reasons
    assert "maximum drawdown above threshold" in result.reasons
    assert "strategy underperformed buy-and-hold" in result.reasons
    assert "insufficient out-of-sample trades" in result.reasons


def test_benchmark_gate_rejects_net_loss_even_if_benchmark_loses_more() -> None:
    report = _report(excess=0.20)
    report.metrics = replace(report.metrics, total_return=-0.02)
    decision = evaluate_benchmark_gate(report)

    assert decision.passed is False
    assert "non-positive net out-of-sample return" in decision.reasons
    assert "strategy underperformed buy-and-hold" not in decision.reasons


def test_benchmark_gate_rejects_break_even_return_by_default() -> None:
    report = _report()
    report.metrics = replace(report.metrics, total_return=0.0)
    decision = evaluate_benchmark_gate(report)

    assert decision.passed is False
    assert "non-positive net out-of-sample return" in decision.reasons


def test_benchmark_gate_rejects_nonfinite_metrics_that_skip_thresholds() -> None:
    report = _report()
    report.metrics = replace(report.metrics, total_return=float("nan"), sharpe=float("nan"))
    decision = evaluate_benchmark_gate(report)

    assert decision.passed is False
    assert "non-finite out-of-sample performance metric" in decision.reasons
    assert "non-positive net out-of-sample return" in decision.reasons


def test_benchmark_gate_rejects_infinite_annualized_volatility() -> None:
    report = _report()
    report.metrics = replace(report.metrics, annualized_volatility=float("inf"))
    decision = evaluate_benchmark_gate(report)

    assert decision.passed is False
    assert "non-finite out-of-sample performance metric" in decision.reasons

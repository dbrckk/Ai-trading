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

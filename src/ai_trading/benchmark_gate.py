from __future__ import annotations

from dataclasses import dataclass

from .backtest import BacktestReport


@dataclass(frozen=True)
class BenchmarkGatePolicy:
    min_folds: int = 4
    min_trades: int = 20
    min_sharpe: float = 0.5
    min_sortino: float = 0.7
    min_calmar: float = 0.5
    max_drawdown: float = 0.25
    min_excess_return: float = 0.0


@dataclass(frozen=True)
class BenchmarkGateResult:
    passed: bool
    reasons: tuple[str, ...]


def evaluate_benchmark_gate(
    report: BacktestReport,
    policy: BenchmarkGatePolicy | None = None,
) -> BenchmarkGateResult:
    policy = policy or BenchmarkGatePolicy()
    reasons: list[str] = []

    if report.folds < policy.min_folds:
        reasons.append("insufficient walk-forward folds")
    if report.trades < policy.min_trades:
        reasons.append("insufficient out-of-sample trades")
    if report.metrics.sharpe < policy.min_sharpe:
        reasons.append("Sharpe below threshold")
    if report.metrics.sortino < policy.min_sortino:
        reasons.append("Sortino below threshold")
    if report.metrics.calmar < policy.min_calmar:
        reasons.append("Calmar below threshold")
    if report.metrics.max_drawdown > policy.max_drawdown:
        reasons.append("maximum drawdown above threshold")
    if report.excess_return < policy.min_excess_return:
        reasons.append("strategy underperformed buy-and-hold")

    return BenchmarkGateResult(passed=not reasons, reasons=tuple(reasons))

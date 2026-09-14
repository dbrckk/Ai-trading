from __future__ import annotations

from dataclasses import dataclass

from .performance import PerformanceMetrics


@dataclass(frozen=True)
class ReadinessPolicy:
    min_burn_in_bars: int = 126
    min_sharpe: float = 0.75
    min_sortino: float = 1.00
    max_drawdown: float = 0.10
    min_total_return: float = 0.0
    min_positive_bootstrap_probability: float = 0.65
    min_regimes_covered: int = 2
    max_consecutive_scheduler_errors: int = 0


@dataclass(frozen=True)
class ReadinessReport:
    ready: bool
    checks_passed: int
    checks_total: int
    reasons: tuple[str, ...]


def evaluate_readiness(
    *,
    metrics: PerformanceMetrics,
    burn_in_bars: int,
    bootstrap_probability_positive: float,
    regimes_covered: int,
    scheduler_errors: int = 0,
    policy: ReadinessPolicy | None = None,
) -> ReadinessReport:
    policy = policy or ReadinessPolicy()
    failures: list[str] = []

    if burn_in_bars < policy.min_burn_in_bars:
        failures.append("insufficient burn-in duration")
    if metrics.sharpe < policy.min_sharpe:
        failures.append("Sharpe below readiness threshold")
    if metrics.sortino < policy.min_sortino:
        failures.append("Sortino below readiness threshold")
    if metrics.max_drawdown > policy.max_drawdown:
        failures.append("drawdown above readiness threshold")
    if metrics.total_return < policy.min_total_return:
        failures.append("total return below readiness threshold")
    if bootstrap_probability_positive < policy.min_positive_bootstrap_probability:
        failures.append("bootstrap confidence below readiness threshold")
    if regimes_covered < policy.min_regimes_covered:
        failures.append("insufficient regime coverage")
    if scheduler_errors > policy.max_consecutive_scheduler_errors:
        failures.append("scheduler reliability below readiness threshold")

    total = 8
    return ReadinessReport(
        ready=not failures,
        checks_passed=total - len(failures),
        checks_total=total,
        reasons=tuple(failures),
    )

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
class ReadinessCheck:
    name: str
    passed: bool
    value: float | int
    threshold: float | int
    comparison: str


@dataclass(frozen=True)
class ReadinessReport:
    ready: bool
    checks_passed: int
    checks_total: int
    reasons: tuple[str, ...]
    checks: tuple[ReadinessCheck, ...] = ()


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
    checks = (
        ReadinessCheck(
            name="Burn-in bars",
            passed=burn_in_bars >= policy.min_burn_in_bars,
            value=burn_in_bars,
            threshold=policy.min_burn_in_bars,
            comparison=">=",
        ),
        ReadinessCheck(
            name="Sharpe",
            passed=metrics.sharpe >= policy.min_sharpe,
            value=metrics.sharpe,
            threshold=policy.min_sharpe,
            comparison=">=",
        ),
        ReadinessCheck(
            name="Sortino",
            passed=metrics.sortino >= policy.min_sortino,
            value=metrics.sortino,
            threshold=policy.min_sortino,
            comparison=">=",
        ),
        ReadinessCheck(
            name="Max drawdown",
            passed=metrics.max_drawdown <= policy.max_drawdown,
            value=metrics.max_drawdown,
            threshold=policy.max_drawdown,
            comparison="<=",
        ),
        ReadinessCheck(
            name="Total return",
            passed=metrics.total_return >= policy.min_total_return,
            value=metrics.total_return,
            threshold=policy.min_total_return,
            comparison=">=",
        ),
        ReadinessCheck(
            name="Bootstrap confidence",
            passed=bootstrap_probability_positive
            >= policy.min_positive_bootstrap_probability,
            value=bootstrap_probability_positive,
            threshold=policy.min_positive_bootstrap_probability,
            comparison=">=",
        ),
        ReadinessCheck(
            name="Regime coverage",
            passed=regimes_covered >= policy.min_regimes_covered,
            value=regimes_covered,
            threshold=policy.min_regimes_covered,
            comparison=">=",
        ),
        ReadinessCheck(
            name="Scheduler errors",
            passed=scheduler_errors <= policy.max_consecutive_scheduler_errors,
            value=scheduler_errors,
            threshold=policy.max_consecutive_scheduler_errors,
            comparison="<=",
        ),
    )

    reason_by_name = {
        "Burn-in bars": "insufficient burn-in duration",
        "Sharpe": "Sharpe below readiness threshold",
        "Sortino": "Sortino below readiness threshold",
        "Max drawdown": "drawdown above readiness threshold",
        "Total return": "total return below readiness threshold",
        "Bootstrap confidence": "bootstrap confidence below readiness threshold",
        "Regime coverage": "insufficient regime coverage",
        "Scheduler errors": "scheduler reliability below readiness threshold",
    }
    failures = [reason_by_name[check.name] for check in checks if not check.passed]
    passed = sum(check.passed for check in checks)
    return ReadinessReport(
        ready=not failures,
        checks_passed=passed,
        checks_total=len(checks),
        reasons=tuple(failures),
        checks=checks,
    )

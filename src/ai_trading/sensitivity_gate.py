from __future__ import annotations

from dataclasses import dataclass
from math import isfinite

from .parameter_sensitivity import SensitivityResult


@dataclass(frozen=True)
class SensitivityGatePolicy:
    min_pass_ratio: float = 0.67
    min_excess_return: float = -0.05
    min_total_return: float = 0.0
    min_sharpe: float = 0.0
    max_drawdown: float = 0.30


@dataclass(frozen=True)
class SensitivityGateResult:
    passed: bool
    scenarios: int
    passing_scenarios: int
    pass_ratio: float
    worst_excess_return: float
    worst_sharpe: float
    worst_drawdown: float
    reasons: tuple[str, ...]


def evaluate_sensitivity_gate(
    results: tuple[SensitivityResult, ...],
    policy: SensitivityGatePolicy | None = None,
) -> SensitivityGateResult:
    policy = policy or SensitivityGatePolicy()
    if not results:
        return SensitivityGateResult(
            passed=False,
            scenarios=0,
            passing_scenarios=0,
            pass_ratio=0.0,
            worst_excess_return=0.0,
            worst_sharpe=0.0,
            worst_drawdown=0.0,
            reasons=("parameter sensitivity results missing",),
        )

    passing = [
        result
        for result in results
        if all(
            isfinite(value)
            for value in (
                result.total_return,
                result.excess_return,
                result.sharpe,
                result.max_drawdown,
            )
        )
        and result.trades > 0
        and result.total_return > policy.min_total_return
        and result.excess_return >= policy.min_excess_return
        and result.sharpe >= policy.min_sharpe
        and 0.0 <= result.max_drawdown <= policy.max_drawdown
    ]
    ratio = len(passing) / len(results)
    reasons: list[str] = []
    if ratio < policy.min_pass_ratio:
        reasons.append("parameter sensitivity pass ratio below threshold")
        if not any(
            isfinite(result.total_return)
            and result.total_return > policy.min_total_return
            for result in results
        ):
            reasons.append("no sensitivity scenario has positive net return")

    worst_excess = min(result.excess_return for result in results)
    worst_sharpe = min(result.sharpe for result in results)
    worst_drawdown = max(result.max_drawdown for result in results)

    return SensitivityGateResult(
        passed=not reasons,
        scenarios=len(results),
        passing_scenarios=len(passing),
        pass_ratio=ratio,
        worst_excess_return=worst_excess,
        worst_sharpe=worst_sharpe,
        worst_drawdown=worst_drawdown,
        reasons=tuple(reasons),
    )

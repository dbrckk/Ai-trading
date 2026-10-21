from __future__ import annotations

from dataclasses import dataclass
from math import isfinite

from .cost_stress import CostStressResult


@dataclass(frozen=True)
class CostStressGatePolicy:
    min_pass_ratio: float = 0.67
    min_excess_return: float = -0.05
    # These total returns already include broker transaction costs and slippage.
    # Outperforming a falling benchmark while losing money is not profit.
    min_total_return: float = 0.0
    min_sharpe: float = 0.0
    max_drawdown: float = 0.30


@dataclass(frozen=True)
class CostStressGateResult:
    passed: bool
    scenarios: int
    passing_scenarios: int
    pass_ratio: float
    worst_excess_return: float
    worst_sharpe: float
    worst_drawdown: float
    reasons: tuple[str, ...]


def evaluate_cost_stress_gate(
    results: tuple[CostStressResult, ...],
    policy: CostStressGatePolicy | None = None,
) -> CostStressGateResult:
    policy = policy or CostStressGatePolicy()
    if not results:
        return CostStressGateResult(
            passed=False,
            scenarios=0,
            passing_scenarios=0,
            pass_ratio=0.0,
            worst_excess_return=0.0,
            worst_sharpe=0.0,
            worst_drawdown=0.0,
            reasons=("cost stress results missing",),
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
        reasons.append("cost stress pass ratio below threshold")
        if not any(
            isfinite(result.total_return)
            and result.total_return > policy.min_total_return
            for result in results
        ):
            reasons.append("no cost-stress scenario has positive net return")

    return CostStressGateResult(
        passed=not reasons,
        scenarios=len(results),
        passing_scenarios=len(passing),
        pass_ratio=ratio,
        worst_excess_return=min(result.excess_return for result in results),
        worst_sharpe=min(result.sharpe for result in results),
        worst_drawdown=max(result.max_drawdown for result in results),
        reasons=tuple(reasons),
    )

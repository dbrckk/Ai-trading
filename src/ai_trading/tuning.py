from __future__ import annotations

from dataclasses import dataclass

from .performance import PerformanceMetrics


@dataclass(frozen=True)
class OptimizationWeights:
    return_weight: float = 1.0
    sharpe_weight: float = 0.35
    sortino_weight: float = 0.15
    drawdown_penalty: float = 1.25


def objective_score(
    metrics: PerformanceMetrics,
    weights: OptimizationWeights | None = None,
) -> float:
    """Risk-aware scalar objective for hyperparameter searches.

    The score intentionally penalizes drawdown so an optimizer cannot
    maximize raw return while silently accepting unacceptable risk.
    """
    weights = weights or OptimizationWeights()
    return float(
        weights.return_weight * metrics.total_return
        + weights.sharpe_weight * metrics.sharpe
        + weights.sortino_weight * metrics.sortino
        - weights.drawdown_penalty * metrics.max_drawdown
    )

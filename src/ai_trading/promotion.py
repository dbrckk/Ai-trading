from __future__ import annotations

from dataclasses import dataclass

from .performance import PerformanceMetrics


@dataclass(frozen=True)
class PromotionPolicy:
    min_sharpe_improvement: float = 0.10
    min_return_improvement: float = 0.00
    max_drawdown_increase: float = 0.02


@dataclass(frozen=True)
class PromotionDecision:
    promote: bool
    reason: str


def evaluate_challenger(
    champion: PerformanceMetrics,
    challenger: PerformanceMetrics,
    policy: PromotionPolicy | None = None,
) -> PromotionDecision:
    policy = policy or PromotionPolicy()

    sharpe_gain = challenger.sharpe - champion.sharpe
    return_gain = challenger.total_return - champion.total_return
    drawdown_increase = challenger.max_drawdown - champion.max_drawdown

    if sharpe_gain < policy.min_sharpe_improvement:
        return PromotionDecision(False, "insufficient Sharpe improvement")
    if return_gain < policy.min_return_improvement:
        return PromotionDecision(False, "insufficient total return improvement")
    if drawdown_increase > policy.max_drawdown_increase:
        return PromotionDecision(False, "drawdown deterioration too large")

    return PromotionDecision(True, "challenger passes promotion policy")

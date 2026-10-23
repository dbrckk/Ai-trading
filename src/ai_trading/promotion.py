from __future__ import annotations

from dataclasses import dataclass
from math import isfinite

from .performance import PerformanceMetrics


@dataclass(frozen=True)
class PromotionPolicy:
    min_sharpe_improvement: float = 0.10
    min_return_improvement: float = 0.00
    max_drawdown_increase: float = 0.02
    min_period_win_rate: float = 0.60

    def __post_init__(self) -> None:
        if not all(
            isfinite(value)
            for value in (
                self.min_sharpe_improvement,
                self.min_return_improvement,
                self.max_drawdown_increase,
                self.min_period_win_rate,
            )
        ):
            raise ValueError("promotion policy thresholds must be finite")
        if self.max_drawdown_increase < 0:
            raise ValueError("max_drawdown_increase must be non-negative")
        if not 0.0 < self.min_period_win_rate <= 1.0:
            raise ValueError("min_period_win_rate must be in (0, 1]")


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

    # A NaN comparison evaluates to False and previously allowed promotion.
    # Require complete finite evidence from both backtests, not only valid deltas.
    for metrics in (champion, challenger):
        if not all(isfinite(value) for value in metrics.as_dict().values()):
            return PromotionDecision(False, "non-finite promotion metrics")
        if not 0.0 <= metrics.max_drawdown <= 1.0:
            return PromotionDecision(False, "invalid promotion drawdown")

    # Relative improvement versus a losing incumbent is not a profitable edge.
    if challenger.total_return <= 0.0:
        return PromotionDecision(False, "challenger lacks positive net return")

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


def evaluate_multi_period_challenger(
    champion_periods: list[PerformanceMetrics],
    challenger_periods: list[PerformanceMetrics],
    policy: PromotionPolicy | None = None,
) -> PromotionDecision:
    policy = policy or PromotionPolicy()
    if len(champion_periods) != len(challenger_periods) or not champion_periods:
        return PromotionDecision(False, "invalid or mismatched evaluation periods")

    # Reject the whole multi-period comparison if any segment contains
    # undefined evidence. Counting it as one loss can still exceed win-rate.
    if any(
        not all(isfinite(value) for value in metrics.as_dict().values())
        or not 0.0 <= metrics.max_drawdown <= 1.0
        for metrics in (*champion_periods, *challenger_periods)
    ):
        return PromotionDecision(False, "invalid multi-period promotion metrics")

    wins = 0
    for champion, challenger in zip(champion_periods, challenger_periods, strict=True):
        decision = evaluate_challenger(champion, challenger, policy)
        if decision.promote:
            wins += 1

    win_rate = wins / len(champion_periods)
    if win_rate < policy.min_period_win_rate:
        return PromotionDecision(
            False,
            f"insufficient period win rate: {win_rate:.1%}",
        )
    return PromotionDecision(
        True,
        f"challenger passes multi-period policy: {win_rate:.1%} win rate",
    )

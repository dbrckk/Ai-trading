from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True)
class PromotionPolicy:
    min_score_improvement: float = 0.0
    min_sharpe_delta: float = -0.05
    min_sortino_delta: float = -0.05
    max_drawdown_increase: float = 0.02
    min_calmar_delta: float = -0.05
    required_metrics: tuple[str, ...] = (
        "sharpe",
        "sortino",
        "max_drawdown",
        "calmar",
    )


@dataclass(frozen=True)
class PromotionDecision:
    approved: bool
    reasons: tuple[str, ...]
    score_delta: float
    metric_deltas: dict[str, float]


def evaluate_promotion(
    *,
    champion_score: float,
    champion_metrics: dict[str, float],
    challenger_score: float,
    challenger_metrics: dict[str, float],
    policy: PromotionPolicy | None = None,
) -> PromotionDecision:
    policy = policy or PromotionPolicy()
    reasons: list[str] = []

    values = [champion_score, challenger_score]
    values.extend(champion_metrics.values())
    values.extend(challenger_metrics.values())
    if any(not math.isfinite(float(value)) for value in values):
        return PromotionDecision(
            approved=False,
            reasons=("non-finite validation metric",),
            score_delta=float("nan"),
            metric_deltas={},
        )

    missing = [
        metric
        for metric in policy.required_metrics
        if metric not in champion_metrics or metric not in challenger_metrics
    ]
    if missing:
        return PromotionDecision(
            approved=False,
            reasons=(f"missing required metrics: {', '.join(sorted(missing))}",),
            score_delta=float(challenger_score - champion_score),
            metric_deltas={},
        )

    score_delta = float(challenger_score - champion_score)
    metric_deltas = {
        name: float(challenger_metrics[name] - champion_metrics[name])
        for name in policy.required_metrics
    }

    if score_delta < policy.min_score_improvement:
        reasons.append("composite score did not improve enough")
    if metric_deltas["sharpe"] < policy.min_sharpe_delta:
        reasons.append("Sharpe degradation exceeds policy")
    if metric_deltas["sortino"] < policy.min_sortino_delta:
        reasons.append("Sortino degradation exceeds policy")
    if metric_deltas["calmar"] < policy.min_calmar_delta:
        reasons.append("Calmar degradation exceeds policy")
    if metric_deltas["max_drawdown"] > policy.max_drawdown_increase:
        reasons.append("max drawdown degradation exceeds policy")

    return PromotionDecision(
        approved=not reasons,
        reasons=tuple(reasons),
        score_delta=score_delta,
        metric_deltas=metric_deltas,
    )

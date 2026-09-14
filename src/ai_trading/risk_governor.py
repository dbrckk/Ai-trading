from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class GovernorPolicy:
    min_data_quality: float = 0.95
    halt_data_quality: float = 0.75
    min_model_confidence: float = 0.55
    flatten_drawdown: float = 0.15
    reduce_drawdown: float = 0.08
    max_stressed_cvar: float = 0.08
    reduce_stressed_cvar: float = 0.05


@dataclass(frozen=True)
class GovernorSignals:
    data_quality: float
    system_healthy: bool
    model_confidence: float
    portfolio_risk_approved: bool
    stress_approved: bool
    stressed_cvar: float
    drawdown: float
    crisis_mode: str
    liquidity_stressed: bool = False


@dataclass(frozen=True)
class GovernorDecision:
    verdict: str
    exposure_scale: float
    allow_rebalance: bool
    flatten: bool
    halt: bool
    reason: str


def evaluate_governor(
    signals: GovernorSignals,
    policy: GovernorPolicy | None = None,
) -> GovernorDecision:
    policy = policy or GovernorPolicy()

    if not signals.system_healthy or signals.data_quality < policy.halt_data_quality:
        return GovernorDecision(
            verdict="HALT",
            exposure_scale=0.0,
            allow_rebalance=False,
            flatten=False,
            halt=True,
            reason="critical operational or data-quality failure",
        )

    if (
        signals.drawdown >= policy.flatten_drawdown
        or signals.stressed_cvar >= policy.max_stressed_cvar
    ):
        return GovernorDecision(
            verdict="FLATTEN",
            exposure_scale=0.0,
            allow_rebalance=True,
            flatten=True,
            halt=False,
            reason="extreme portfolio or stress risk",
        )

    if (
        not signals.portfolio_risk_approved
        or signals.data_quality < policy.min_data_quality
    ):
        return GovernorDecision(
            verdict="FREEZE",
            exposure_scale=1.0,
            allow_rebalance=False,
            flatten=False,
            halt=False,
            reason="risk gate or data-quality gate failed",
        )

    if (
        not signals.stress_approved
        or signals.crisis_mode in {"cautious", "defensive", "capital-preservation"}
        or signals.drawdown >= policy.reduce_drawdown
        or signals.stressed_cvar >= policy.reduce_stressed_cvar
        or signals.liquidity_stressed
        or signals.model_confidence < policy.min_model_confidence
    ):
        return GovernorDecision(
            verdict="REDUCE",
            exposure_scale=0.50,
            allow_rebalance=True,
            flatten=False,
            halt=False,
            reason="elevated aggregate risk",
        )

    return GovernorDecision(
        verdict="TRADE",
        exposure_scale=1.0,
        allow_rebalance=True,
        flatten=False,
        halt=False,
        reason="all global risk gates passed",
    )

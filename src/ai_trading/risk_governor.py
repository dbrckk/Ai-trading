from __future__ import annotations

from dataclasses import dataclass
from math import isfinite


@dataclass(frozen=True)
class GovernorPolicy:
    min_data_quality: float = 0.95
    halt_data_quality: float = 0.75
    min_model_confidence: float = 0.55
    flatten_drawdown: float = 0.15
    reduce_drawdown: float = 0.08
    max_stressed_cvar: float = 0.08
    reduce_stressed_cvar: float = 0.05
    halt_recovery_failures: int = 4
    halt_recovery_fallback_depth: int = 5
    degraded_recovery_exposure_scale: float = 0.35

    def __post_init__(self) -> None:
        """Reject unsafe/undefined gates before a risk policy can authorize trade."""
        bounds = (
            ("min_data_quality", self.min_data_quality),
            ("halt_data_quality", self.halt_data_quality),
            ("min_model_confidence", self.min_model_confidence),
            ("flatten_drawdown", self.flatten_drawdown),
            ("reduce_drawdown", self.reduce_drawdown),
            ("max_stressed_cvar", self.max_stressed_cvar),
            ("reduce_stressed_cvar", self.reduce_stressed_cvar),
            ("degraded_recovery_exposure_scale", self.degraded_recovery_exposure_scale),
        )
        for name, value in bounds:
            if not isinstance(value, (int, float)) or not isfinite(value) or not 0.0 <= value <= 1.0:
                raise ValueError(f"{name} must be finite and in [0, 1]")
        if not self.halt_data_quality <= self.min_data_quality:
            raise ValueError("halt_data_quality must not exceed min_data_quality")
        if not self.reduce_drawdown <= self.flatten_drawdown:
            raise ValueError("reduce_drawdown must not exceed flatten_drawdown")
        if not self.reduce_stressed_cvar <= self.max_stressed_cvar:
            raise ValueError("reduce_stressed_cvar must not exceed max_stressed_cvar")
        if not 0.0 < self.degraded_recovery_exposure_scale <= 1.0:
            raise ValueError("degraded recovery exposure scale must be in (0, 1]")
        for name, value in (
            ("halt_recovery_failures", self.halt_recovery_failures),
            ("halt_recovery_fallback_depth", self.halt_recovery_fallback_depth),
        ):
            if type(value) is not int or value <= 0:
                raise ValueError(f"{name} must be a positive integer")


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
    recovery_degraded: bool = False
    recovery_recent_failures: int = 0
    recovery_fallback_depth: int = 0


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

    # NaN comparisons are false, which would otherwise let corrupt risk
    # telemetry fall through to TRADE or REDUCE. Stop issuing paper orders.
    if (
        any(
            not isfinite(value)
            for value in (
                signals.data_quality,
                signals.model_confidence,
                signals.stressed_cvar,
                signals.drawdown,
                signals.recovery_recent_failures,
                signals.recovery_fallback_depth,
            )
        )
        or not 0.0 <= signals.data_quality <= 1.0
        or not 0.0 <= signals.model_confidence <= 1.0
        or signals.stressed_cvar < 0.0
        or signals.drawdown < 0.0
        or signals.recovery_recent_failures < 0
        or signals.recovery_fallback_depth < 0
    ):
        return GovernorDecision(
            verdict="HALT",
            exposure_scale=0.0,
            allow_rebalance=False,
            flatten=False,
            halt=True,
            reason="invalid risk governor signal",
        )

    if (
        not signals.system_healthy
        or signals.data_quality < policy.halt_data_quality
        or signals.recovery_recent_failures >= policy.halt_recovery_failures
        or signals.recovery_fallback_depth >= policy.halt_recovery_fallback_depth
    ):
        return GovernorDecision(
            verdict="HALT",
            exposure_scale=0.0,
            allow_rebalance=False,
            flatten=False,
            halt=True,
            reason="critical operational, recovery, or data-quality failure",
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

    if signals.recovery_degraded:
        return GovernorDecision(
            verdict="REDUCE",
            exposure_scale=policy.degraded_recovery_exposure_scale,
            allow_rebalance=True,
            flatten=False,
            halt=False,
            reason="recovery health degraded",
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

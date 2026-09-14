from __future__ import annotations

from dataclasses import dataclass

from .governor_state_store import GovernorState
from .qualification_guard import validate_qualification_record
from .qualification_store import QualificationRecord
from .readiness_release import ReadinessReleaseVerification
from .readiness_score import CompositeReadiness, ReadinessChainReport
from .readiness_trend import ReadinessTrend
from .reliability import ReliabilityReport
from .resilience import ResilienceState


@dataclass(frozen=True)
class DeploymentReadinessPolicy:
    min_reliability_score: float = 95.0
    min_normal_ratio: float = 0.95
    max_halt_ratio: float = 0.005
    max_mttr_seconds: float = 300.0
    min_observation_seconds: float = 604_800.0
    max_qualification_age_hours: float = 24.0
    require_composite_score: bool = True
    min_composite_score: float = 90.0
    require_stable_trend: bool = True
    require_release_manifest: bool = True


@dataclass(frozen=True)
class DeploymentReadiness:
    allowed: bool
    reasons: tuple[str, ...]


def evaluate_deployment_readiness(
    record: QualificationRecord | None,
    *,
    reliability: ReliabilityReport | None,
    resilience: ResilienceState,
    governor: GovernorState,
    symbols: tuple[str, ...],
    period: str,
    interval: str,
    policy: DeploymentReadinessPolicy | None = None,
    composite: CompositeReadiness | None = None,
    trend: ReadinessTrend | None = None,
    readiness_chain: ReadinessChainReport | None = None,
    release_verification: ReadinessReleaseVerification | None = None,
) -> DeploymentReadiness:
    policy = policy or DeploymentReadinessPolicy()
    reasons: list[str] = []

    if reliability is None:
        reasons.append("reliability report missing")
    guard = validate_qualification_record(
        record,
        symbols=symbols,
        period=period,
        interval=interval,
        max_age_hours=policy.max_qualification_age_hours,
        reliability=reliability,
        min_reliability_score=policy.min_reliability_score,
        min_normal_ratio=policy.min_normal_ratio,
        max_halt_ratio=policy.max_halt_ratio,
        max_mttr_seconds=policy.max_mttr_seconds,
        min_observation_seconds=policy.min_observation_seconds,
    )
    reasons.extend(guard.reasons)

    if resilience.mode != "NORMAL":
        reasons.append("resilience mode is not NORMAL")
    if resilience.instability_status != "stable":
        reasons.append("resilience instability is not stable")
    if governor.verdict != "TRADE":
        reasons.append("governor verdict is not TRADE")
    if governor.consecutive_halts != 0:
        reasons.append("governor halt streak is not cleared")
    if policy.require_composite_score:
        if composite is None:
            reasons.append("composite readiness score missing")
        else:
            if not composite.passed:
                reasons.append("composite readiness policy failed")
            if composite.score < policy.min_composite_score:
                reasons.append("composite readiness score below deployment threshold")
    if policy.require_stable_trend:
        if trend is None:
            reasons.append("readiness trend missing")
        elif trend.status != "stable":
            reasons.append("readiness trend is not stable")
    if readiness_chain is None:
        reasons.append("readiness history integrity report missing")
    elif not readiness_chain.valid:
        reasons.append("readiness history integrity check failed")
    if policy.require_release_manifest:
        if release_verification is None:
            reasons.append("readiness release manifest missing")
        elif not release_verification.valid:
            reasons.append("readiness release verification failed")

    return DeploymentReadiness(
        allowed=not reasons,
        reasons=tuple(dict.fromkeys(reasons)),
    )

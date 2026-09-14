from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from .qualification_store import QualificationRecord
from .reliability import ReliabilityReport


@dataclass(frozen=True)
class QualificationGuardResult:
    allowed: bool
    reasons: tuple[str, ...]


def validate_qualification_record(
    record: QualificationRecord | None,
    *,
    symbols: tuple[str, ...],
    period: str,
    interval: str,
    max_age_hours: float = 24.0,
    reliability: ReliabilityReport | None = None,
    min_reliability_score: float = 90.0,
    min_normal_ratio: float = 0.90,
    max_halt_ratio: float = 0.01,
    max_mttr_seconds: float | None = None,
    min_observation_seconds: float = 0.0,
) -> QualificationGuardResult:
    reasons: list[str] = []

    if record is None:
        return QualificationGuardResult(False, ("qualification report missing",))

    if not record.passed:
        reasons.append("qualification report is not PASS")

    try:
        created = datetime.fromisoformat(record.created_at_utc)
        if created.tzinfo is None:
            created = created.replace(tzinfo=UTC)
        age_hours = (datetime.now(UTC) - created).total_seconds() / 3600.0
        if age_hours > max_age_hours:
            reasons.append("qualification report is stale")
    except ValueError:
        reasons.append("qualification timestamp is invalid")

    if tuple(sorted(record.symbols)) != tuple(sorted(symbols)):
        reasons.append("qualification symbols do not match")
    if record.period != period:
        reasons.append("qualification period does not match")
    if record.interval != interval:
        reasons.append("qualification interval does not match")

    effective_reliability = reliability
    if effective_reliability is None and record.reliability_score is not None:
        effective_reliability = ReliabilityReport(
            observation_seconds=float(record.reliability_observation_seconds or 0.0),
            normal_ratio=float(record.normal_ratio or 0.0),
            cautious_ratio=0.0,
            degraded_ratio=0.0,
            recovery_ratio=0.0,
            cooldown_ratio=0.0,
            halt_ratio=float(record.halt_ratio or 0.0),
            halt_count=0,
            incident_count=0,
            mttr_seconds=record.mttr_seconds,
            mtbf_seconds=record.mtbf_seconds,
            reliability_score=float(record.reliability_score),
        )

    if effective_reliability is not None:
        if effective_reliability.observation_seconds < min_observation_seconds:
            reasons.append("reliability observation window too short")
        if effective_reliability.reliability_score < min_reliability_score:
            reasons.append("reliability score below qualification threshold")
        if effective_reliability.normal_ratio < min_normal_ratio:
            reasons.append("normal-state ratio below qualification threshold")
        if effective_reliability.halt_ratio > max_halt_ratio:
            reasons.append("halt-state ratio exceeds qualification threshold")
        if (
            max_mttr_seconds is not None
            and effective_reliability.mttr_seconds is not None
            and effective_reliability.mttr_seconds > max_mttr_seconds
        ):
            reasons.append("MTTR exceeds qualification threshold")

    return QualificationGuardResult(
        allowed=not reasons,
        reasons=tuple(reasons),
    )

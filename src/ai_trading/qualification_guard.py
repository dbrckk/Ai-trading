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

    if reliability is not None:
        if reliability.reliability_score < min_reliability_score:
            reasons.append("reliability score below qualification threshold")
        if reliability.normal_ratio < min_normal_ratio:
            reasons.append("normal-state ratio below qualification threshold")
        if reliability.halt_ratio > max_halt_ratio:
            reasons.append("halt-state ratio exceeds qualification threshold")
        if (
            max_mttr_seconds is not None
            and reliability.mttr_seconds is not None
            and reliability.mttr_seconds > max_mttr_seconds
        ):
            reasons.append("MTTR exceeds qualification threshold")

    return QualificationGuardResult(
        allowed=not reasons,
        reasons=tuple(reasons),
    )

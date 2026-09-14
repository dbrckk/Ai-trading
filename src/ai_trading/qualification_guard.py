from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from .qualification_store import QualificationRecord


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

    return QualificationGuardResult(
        allowed=not reasons,
        reasons=tuple(reasons),
    )

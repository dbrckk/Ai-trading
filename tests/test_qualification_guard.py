from datetime import UTC, datetime

from ai_trading.qualification_guard import validate_qualification_record
from ai_trading.qualification_store import QualificationRecord


def test_qualification_guard_requires_matching_scope() -> None:
    record = QualificationRecord(
        created_at_utc=datetime.now(UTC).isoformat(),
        passed=True,
        success_ratio=1.0,
        reasons=(),
        cycles=100,
        failures=0,
        max_drawdown=0.02,
        governor_verdict="TRADE",
        crisis_mode="normal",
        symbols=("GC=F", "SI=F"),
        period="2y",
        interval="1d",
    )

    ok = validate_qualification_record(
        record,
        symbols=("GC=F", "SI=F"),
        period="2y",
        interval="1d",
    )
    assert ok.allowed

    bad = validate_qualification_record(
        record,
        symbols=("GC=F", "CL=F"),
        period="2y",
        interval="1d",
    )
    assert not bad.allowed

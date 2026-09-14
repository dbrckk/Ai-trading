from datetime import UTC, datetime

from ai_trading.qualification_guard import validate_qualification_record
from ai_trading.qualification_store import QualificationRecord
from ai_trading.reliability import ReliabilityReport


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



def test_qualification_guard_rejects_low_reliability() -> None:
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
        symbols=("GC=F",),
        period="2y",
        interval="1d",
    )
    reliability = ReliabilityReport(
        observation_seconds=10_000.0,
        normal_ratio=0.80,
        cautious_ratio=0.05,
        degraded_ratio=0.05,
        recovery_ratio=0.03,
        cooldown_ratio=0.02,
        halt_ratio=0.05,
        halt_count=2,
        incident_count=4,
        mttr_seconds=900.0,
        mtbf_seconds=2_000.0,
        reliability_score=82.0,
    )

    result = validate_qualification_record(
        record,
        symbols=("GC=F",),
        period="2y",
        interval="1d",
        reliability=reliability,
        min_reliability_score=90.0,
        min_normal_ratio=0.90,
        max_halt_ratio=0.01,
        max_mttr_seconds=600.0,
    )

    assert not result.allowed
    assert "reliability score below qualification threshold" in result.reasons
    assert "normal-state ratio below qualification threshold" in result.reasons
    assert "halt-state ratio exceeds qualification threshold" in result.reasons
    assert "MTTR exceeds qualification threshold" in result.reasons

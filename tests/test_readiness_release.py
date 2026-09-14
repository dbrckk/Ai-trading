from datetime import UTC, datetime

from ai_trading.governor_state_store import GovernorState
from ai_trading.qualification_store import QualificationRecord
from ai_trading.readiness_release import (
    ReadinessReleaseStore,
    create_readiness_release,
    verify_readiness_release,
)
from ai_trading.readiness_score import (
    ReadinessChainReport,
    ReadinessComponents,
    evaluate_composite_readiness,
)
from ai_trading.readiness_trend import ReadinessTrend
from ai_trading.resilience import ResilienceState


def composite():
    return evaluate_composite_readiness(
        ReadinessComponents(
            performance=96.0,
            robustness=95.0,
            reliability=98.0,
            recovery=96.0,
            data_quality=99.0,
            model_stability=95.0,
            execution_quality=94.0,
        )
    )


def qualification() -> QualificationRecord:
    return QualificationRecord(
        created_at_utc=datetime.now(UTC).isoformat(),
        passed=True,
        success_ratio=1.0,
        reasons=(),
        cycles=500,
        failures=0,
        max_drawdown=0.02,
        governor_verdict="TRADE",
        crisis_mode="normal",
        symbols=("GC=F",),
        period="2y",
        interval="1d",
    )


def trend() -> ReadinessTrend:
    return ReadinessTrend(
        status="stable",
        observations=5,
        latest_score=95.0,
        score_change=1.0,
        pass_ratio=1.0,
        reasons=(),
    )


def test_readiness_release_round_trip(tmp_path) -> None:
    comp = composite()
    qual = qualification()
    gov = GovernorState(verdict="TRADE", reason="healthy", consecutive_halts=0)
    res = ResilienceState(mode="NORMAL", instability_status="stable")
    chain = ReadinessChainReport(valid=True, records=5, legacy_records=0)

    release = create_readiness_release(
        composite=comp,
        chain_head="abc123",
        chain=chain,
        qualification=qual,
        governor=gov,
        resilience=res,
        trend=trend(),
        created_at_utc="2026-09-14T20:00:00+00:00",
        signing_key="test-secret",
    )
    store = ReadinessReleaseStore(tmp_path / "release.json")
    store.save(release)
    loaded = store.load()

    assert loaded == release
    verification = verify_readiness_release(
        loaded,
        composite=comp,
        chain_head="abc123",
        chain=chain,
        qualification=qual,
        governor=gov,
        resilience=res,
        trend=trend(),
        signing_key="test-secret",
    )
    assert verification.valid


def test_readiness_release_rejects_changed_governor() -> None:
    comp = composite()
    qual = qualification()
    gov = GovernorState(verdict="TRADE")
    res = ResilienceState(mode="NORMAL")
    chain = ReadinessChainReport(valid=True, records=5, legacy_records=0)
    release = create_readiness_release(
        composite=comp,
        chain_head="abc123",
        chain=chain,
        qualification=qual,
        governor=gov,
        resilience=res,
        trend=trend(),
        signing_key="test-secret",
    )

    verification = verify_readiness_release(
        release,
        composite=comp,
        chain_head="abc123",
        chain=chain,
        qualification=qual,
        governor=GovernorState(verdict="HALT", consecutive_halts=1),
        resilience=res,
        trend=trend(),
        signing_key="test-secret",
    )

    assert not verification.valid
    assert verification.reason == "readiness release hash mismatch"


def test_readiness_release_rejects_changed_chain_head() -> None:
    comp = composite()
    qual = qualification()
    gov = GovernorState(verdict="TRADE")
    res = ResilienceState(mode="NORMAL")
    chain = ReadinessChainReport(valid=True, records=5, legacy_records=0)
    release = create_readiness_release(
        composite=comp,
        chain_head="abc123",
        chain=chain,
        qualification=qual,
        governor=gov,
        resilience=res,
        trend=trend(),
        signing_key="test-secret",
    )

    verification = verify_readiness_release(
        release,
        composite=comp,
        chain_head="different",
        chain=chain,
        qualification=qual,
        governor=gov,
        resilience=res,
        trend=trend(),
        signing_key="test-secret",
    )

    assert not verification.valid
    assert verification.reason == "readiness chain head changed"


def test_readiness_release_is_content_addressed() -> None:
    comp = composite()
    qual = qualification()
    gov = GovernorState(verdict="TRADE")
    res = ResilienceState(mode="NORMAL")
    chain = ReadinessChainReport(valid=True, records=5, legacy_records=0)

    first = create_readiness_release(
        composite=comp,
        chain_head="abc123",
        chain=chain,
        qualification=qual,
        governor=gov,
        resilience=res,
        trend=trend(),
        created_at_utc="2026-09-14T20:00:00+00:00",
        signing_key="test-secret",
    )
    second = create_readiness_release(
        composite=comp,
        chain_head="abc123",
        chain=chain,
        qualification=qual,
        governor=gov,
        resilience=res,
        trend=trend(),
        created_at_utc="2026-09-14T20:00:00+00:00",
        signing_key="test-secret",
    )

    assert first.release_hash == second.release_hash



def test_readiness_release_rejects_wrong_signing_key() -> None:
    comp = composite()
    qual = qualification()
    gov = GovernorState(verdict="TRADE")
    res = ResilienceState(mode="NORMAL")
    chain = ReadinessChainReport(valid=True, records=5, legacy_records=0)
    release = create_readiness_release(
        composite=comp,
        chain_head="abc123",
        chain=chain,
        qualification=qual,
        governor=gov,
        resilience=res,
        trend=trend(),
        signing_key="correct-secret",
    )

    verification = verify_readiness_release(
        release,
        composite=comp,
        chain_head="abc123",
        chain=chain,
        qualification=qual,
        governor=gov,
        resilience=res,
        trend=trend(),
        signing_key="wrong-secret",
    )

    assert not verification.valid
    assert verification.reason == "readiness release signature invalid"


def test_readiness_release_rejects_unsigned_manifest_by_default() -> None:
    comp = composite()
    qual = qualification()
    gov = GovernorState(verdict="TRADE")
    res = ResilienceState(mode="NORMAL")
    chain = ReadinessChainReport(valid=True, records=5, legacy_records=0)
    release = create_readiness_release(
        composite=comp,
        chain_head="abc123",
        chain=chain,
        qualification=qual,
        governor=gov,
        resilience=res,
        trend=trend(),
    )

    verification = verify_readiness_release(
        release,
        composite=comp,
        chain_head="abc123",
        chain=chain,
        qualification=qual,
        governor=gov,
        resilience=res,
        trend=trend(),
    )

    assert not verification.valid
    assert verification.reason == "readiness release signature missing"

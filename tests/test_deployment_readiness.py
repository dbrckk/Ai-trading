from datetime import UTC, datetime

from ai_trading.deployment_readiness import evaluate_deployment_readiness
from ai_trading.governor_state_store import GovernorState
from ai_trading.qualification_store import QualificationRecord
from ai_trading.readiness_release import ReadinessReleaseVerification
from ai_trading.readiness_score import (
    ReadinessChainReport,
    ReadinessComponents,
    evaluate_composite_readiness,
)
from ai_trading.readiness_trend import ReadinessTrend
from ai_trading.reliability import ReliabilityReport
from ai_trading.resilience import ResilienceState


def qualified_record() -> QualificationRecord:
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


def composite_score():
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


def stable_trend() -> ReadinessTrend:
    return ReadinessTrend(
        status="stable",
        observations=5,
        latest_score=95.0,
        score_change=1.0,
        pass_ratio=1.0,
        reasons=(),
    )


def reliable_report() -> ReliabilityReport:
    return ReliabilityReport(
        observation_seconds=700_000.0,
        normal_ratio=0.98,
        cautious_ratio=0.01,
        degraded_ratio=0.005,
        recovery_ratio=0.005,
        cooldown_ratio=0.0,
        halt_ratio=0.0,
        halt_count=0,
        incident_count=2,
        mttr_seconds=120.0,
        mtbf_seconds=300_000.0,
        reliability_score=98.0,
    )


def test_deployment_readiness_allows_only_fully_healthy_state() -> None:
    result = evaluate_deployment_readiness(
        qualified_record(),
        reliability=reliable_report(),
        resilience=ResilienceState(
            mode="NORMAL",
            instability_status="stable",
        ),
        governor=GovernorState(
            verdict="TRADE",
            reason="healthy",
            consecutive_halts=0,
        ),
        symbols=("GC=F",),
        period="2y",
        interval="1d",
        composite=composite_score(),
        trend=stable_trend(),
        readiness_chain=ReadinessChainReport(valid=True, records=5, legacy_records=0),
        release_verification=ReadinessReleaseVerification(valid=True),
        quantitative_reproducible=True,
        quantitative_evidence_age_hours=1.0,
        dataset_observation_age_hours=1.0,
    )

    assert result.allowed
    assert not result.reasons


def test_deployment_readiness_fails_closed_on_resilience_or_governor() -> None:
    result = evaluate_deployment_readiness(
        qualified_record(),
        reliability=reliable_report(),
        resilience=ResilienceState(
            mode="DEGRADED",
            instability_status="degraded",
        ),
        governor=GovernorState(
            verdict="HALT",
            reason="critical",
            consecutive_halts=2,
        ),
        symbols=("GC=F",),
        period="2y",
        interval="1d",
        composite=composite_score(),
        trend=stable_trend(),
        readiness_chain=ReadinessChainReport(valid=True, records=5, legacy_records=0),
        release_verification=ReadinessReleaseVerification(valid=True),
        quantitative_reproducible=True,
        quantitative_evidence_age_hours=1.0,
        dataset_observation_age_hours=1.0,
    )

    assert not result.allowed
    assert "resilience mode is not NORMAL" in result.reasons
    assert "resilience instability is not stable" in result.reasons
    assert "governor verdict is not TRADE" in result.reasons
    assert "governor halt streak is not cleared" in result.reasons


def test_deployment_readiness_rejects_short_reliability_history() -> None:
    reliability = reliable_report()
    reliability = ReliabilityReport(
        **{
            **reliability.__dict__,
            "observation_seconds": 86_400.0,
        }
    )

    result = evaluate_deployment_readiness(
        qualified_record(),
        reliability=reliability,
        resilience=ResilienceState(mode="NORMAL"),
        governor=GovernorState(verdict="TRADE"),
        symbols=("GC=F",),
        period="2y",
        interval="1d",
        composite=composite_score(),
        trend=stable_trend(),
        readiness_chain=ReadinessChainReport(valid=True, records=5, legacy_records=0),
        release_verification=ReadinessReleaseVerification(valid=True),
        quantitative_reproducible=True,
        quantitative_evidence_age_hours=1.0,
        dataset_observation_age_hours=1.0,
    )

    assert not result.allowed
    assert "reliability observation window too short" in result.reasons


def test_deployment_readiness_rejects_missing_composite_score() -> None:
    result = evaluate_deployment_readiness(
        qualified_record(),
        reliability=reliable_report(),
        resilience=ResilienceState(mode="NORMAL"),
        governor=GovernorState(verdict="TRADE"),
        symbols=("GC=F",),
        period="2y",
        interval="1d",
        composite=None,
        trend=stable_trend(),
        readiness_chain=ReadinessChainReport(valid=True, records=5, legacy_records=0),
        release_verification=ReadinessReleaseVerification(valid=True),
        quantitative_reproducible=True,
        quantitative_evidence_age_hours=1.0,
        dataset_observation_age_hours=1.0,
    )

    assert not result.allowed
    assert "composite readiness score missing" in result.reasons


def test_deployment_readiness_rejects_unstable_trend() -> None:
    trend = ReadinessTrend(
        status="degraded",
        observations=5,
        latest_score=92.0,
        score_change=-8.0,
        pass_ratio=1.0,
        reasons=("readiness score trend declining",),
    )
    result = evaluate_deployment_readiness(
        qualified_record(),
        reliability=reliable_report(),
        resilience=ResilienceState(mode="NORMAL"),
        governor=GovernorState(verdict="TRADE"),
        symbols=("GC=F",),
        period="2y",
        interval="1d",
        composite=composite_score(),
        trend=trend,
        readiness_chain=ReadinessChainReport(valid=True, records=5, legacy_records=0),
        release_verification=ReadinessReleaseVerification(valid=True),
        quantitative_reproducible=True,
        quantitative_evidence_age_hours=1.0,
        dataset_observation_age_hours=1.0,
    )

    assert not result.allowed
    assert "readiness trend is not stable" in result.reasons


def test_deployment_readiness_rejects_invalid_readiness_chain() -> None:
    result = evaluate_deployment_readiness(
        qualified_record(),
        reliability=reliable_report(),
        resilience=ResilienceState(mode="NORMAL"),
        governor=GovernorState(verdict="TRADE"),
        symbols=("GC=F",),
        period="2y",
        interval="1d",
        composite=composite_score(),
        trend=stable_trend(),
        readiness_chain=ReadinessChainReport(
            valid=False,
            records=5,
            legacy_records=0,
            reason="tampered",
        ),
    )

    assert not result.allowed
    assert "readiness history integrity check failed" in result.reasons



def test_deployment_readiness_rejects_invalid_release_manifest() -> None:
    result = evaluate_deployment_readiness(
        qualified_record(),
        reliability=reliable_report(),
        resilience=ResilienceState(mode="NORMAL"),
        governor=GovernorState(verdict="TRADE"),
        symbols=("GC=F",),
        period="2y",
        interval="1d",
        composite=composite_score(),
        trend=stable_trend(),
        readiness_chain=ReadinessChainReport(valid=True, records=5, legacy_records=0),
        release_verification=ReadinessReleaseVerification(
            valid=False,
            reason="readiness release hash mismatch",
        ),
    )

    assert not result.allowed
    assert "readiness release verification failed" in result.reasons


def test_deployment_readiness_rejects_non_reproducible_quantitative_evidence() -> None:
    result = evaluate_deployment_readiness(
        qualified_record(),
        reliability=reliable_report(),
        resilience=ResilienceState(mode="NORMAL"),
        governor=GovernorState(verdict="TRADE"),
        symbols=("GC=F",),
        period="2y",
        interval="1d",
        composite=composite_score(),
        trend=stable_trend(),
        readiness_chain=ReadinessChainReport(valid=True, records=5, legacy_records=0),
        release_verification=ReadinessReleaseVerification(valid=True),
        quantitative_reproducible=False,
        quantitative_evidence_age_hours=1.0,
        dataset_observation_age_hours=1.0,
    )

    assert not result.allowed
    assert "quantitative evidence is not reproducible" in result.reasons


def test_deployment_readiness_rejects_stale_quantitative_evidence() -> None:
    result = evaluate_deployment_readiness(
        qualified_record(),
        reliability=reliable_report(),
        resilience=ResilienceState(mode="NORMAL"),
        governor=GovernorState(verdict="TRADE"),
        symbols=("GC=F",),
        period="2y",
        interval="1d",
        composite=composite_score(),
        trend=stable_trend(),
        readiness_chain=ReadinessChainReport(valid=True, records=5, legacy_records=0),
        release_verification=ReadinessReleaseVerification(valid=True),
        quantitative_reproducible=True,
        quantitative_evidence_age_hours=25.0,
        dataset_observation_age_hours=1.0,
    )

    assert not result.allowed
    assert "quantitative evidence is stale" in result.reasons


def test_deployment_readiness_rejects_unknown_quantitative_evidence_age() -> None:
    result = evaluate_deployment_readiness(
        qualified_record(),
        reliability=reliable_report(),
        resilience=ResilienceState(mode="NORMAL"),
        governor=GovernorState(verdict="TRADE"),
        symbols=("GC=F",),
        period="2y",
        interval="1d",
        composite=composite_score(),
        trend=stable_trend(),
        readiness_chain=ReadinessChainReport(valid=True, records=5, legacy_records=0),
        release_verification=ReadinessReleaseVerification(valid=True),
        quantitative_reproducible=True,
        quantitative_evidence_age_hours=None,
        dataset_observation_age_hours=1.0,
    )

    assert not result.allowed
    assert "quantitative evidence age is unknown" in result.reasons


def test_deployment_readiness_accepts_dataset_observation_at_age_limit() -> None:
    result = evaluate_deployment_readiness(
        qualified_record(),
        reliability=reliable_report(),
        resilience=ResilienceState(mode="NORMAL"),
        governor=GovernorState(verdict="TRADE"),
        symbols=("GC=F",),
        period="2y",
        interval="1d",
        composite=composite_score(),
        trend=stable_trend(),
        readiness_chain=ReadinessChainReport(valid=True, records=5, legacy_records=0),
        release_verification=ReadinessReleaseVerification(valid=True),
        quantitative_reproducible=True,
        quantitative_evidence_age_hours=1.0,
        dataset_observation_age_hours=72.0,
    )

    assert result.allowed


def test_deployment_readiness_rejects_stale_dataset_observation() -> None:
    result = evaluate_deployment_readiness(
        qualified_record(),
        reliability=reliable_report(),
        resilience=ResilienceState(mode="NORMAL"),
        governor=GovernorState(verdict="TRADE"),
        symbols=("GC=F",),
        period="2y",
        interval="1d",
        composite=composite_score(),
        trend=stable_trend(),
        readiness_chain=ReadinessChainReport(valid=True, records=5, legacy_records=0),
        release_verification=ReadinessReleaseVerification(valid=True),
        quantitative_reproducible=True,
        quantitative_evidence_age_hours=1.0,
        dataset_observation_age_hours=72.01,
    )

    assert not result.allowed
    assert "dataset observations are stale" in result.reasons


def test_deployment_readiness_rejects_unknown_dataset_observation_age() -> None:
    result = evaluate_deployment_readiness(
        qualified_record(),
        reliability=reliable_report(),
        resilience=ResilienceState(mode="NORMAL"),
        governor=GovernorState(verdict="TRADE"),
        symbols=("GC=F",),
        period="2y",
        interval="1d",
        composite=composite_score(),
        trend=stable_trend(),
        readiness_chain=ReadinessChainReport(valid=True, records=5, legacy_records=0),
        release_verification=ReadinessReleaseVerification(valid=True),
        quantitative_reproducible=True,
        quantitative_evidence_age_hours=1.0,
        dataset_observation_age_hours=None,
    )

    assert not result.allowed
    assert "dataset observation age is unknown" in result.reasons

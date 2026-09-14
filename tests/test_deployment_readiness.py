from datetime import UTC, datetime

from ai_trading.deployment_readiness import evaluate_deployment_readiness
from ai_trading.governor_state_store import GovernorState
from ai_trading.qualification_store import QualificationRecord
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
    )

    assert not result.allowed
    assert "reliability observation window too short" in result.reasons

import pandas as pd

from ai_trading.data_quality import DataQualityReport
from ai_trading.global_allocator import GlobalAllocationReport
from ai_trading.model_quality import ModelQuality
from ai_trading.performance import PerformanceMetrics
from ai_trading.readiness_evidence import (
    ReadinessEvidence,
    build_readiness_components,
    execution_quality_component,
    model_stability_component,
)
from ai_trading.recovery_health import RecoveryHealth
from ai_trading.reliability import ReliabilityReport
from ai_trading.robustness import BootstrapReport


def strong_evidence() -> ReadinessEvidence:
    return ReadinessEvidence(
        performance=PerformanceMetrics(
            total_return=0.25,
            annualized_return=0.18,
            annualized_volatility=0.12,
            sharpe=1.8,
            sortino=2.2,
            max_drawdown=0.06,
            calmar=2.0,
        ),
        robustness=BootstrapReport(
            median_return=0.20,
            p05_return=0.04,
            p95_return=0.40,
            probability_positive=0.95,
            probability_loss_gt_10pct=0.01,
        ),
        reliability=ReliabilityReport(
            observation_seconds=700_000.0,
            normal_ratio=0.98,
            cautious_ratio=0.01,
            degraded_ratio=0.005,
            recovery_ratio=0.005,
            cooldown_ratio=0.0,
            halt_ratio=0.0,
            halt_count=0,
            incident_count=1,
            mttr_seconds=60.0,
            mtbf_seconds=None,
            reliability_score=98.0,
        ),
        recovery=RecoveryHealth(
            status="healthy",
            recent_attempts=1,
            recent_failures=0,
            max_fallback_depth=0,
            reasons=(),
        ),
        data_quality=DataQualityReport(
            score=0.99,
            completeness=1.0,
            duplicate_fraction=0.0,
            invalid_price_fraction=0.0,
            ohlc_violation_fraction=0.0,
            stale_fraction=0.01,
            valid=True,
            reasons=(),
        ),
        model_quality=ModelQuality(
            score=0.94,
            accuracy=0.72,
            brier=0.12,
            directional_edge=0.20,
            observations=120,
        ),
        execution=GlobalAllocationReport(
            weights=pd.Series({"A": 0.5, "B": 0.5}),
            cvar=0.02,
            expected_return=0.01,
            turnover=0.05,
            estimated_cost=0.0001,
            approved=True,
            reasons=(),
        ),
    )


def test_build_readiness_components_from_strong_evidence() -> None:
    components = build_readiness_components(strong_evidence())

    assert components.performance > 80.0
    assert components.robustness > 85.0
    assert components.reliability == 98.0
    assert components.recovery == 100.0
    assert components.data_quality == 99.0
    assert components.model_stability == 94.0
    assert components.execution_quality > 90.0


def test_model_stability_penalizes_small_sample() -> None:
    report = ModelQuality(
        score=0.90,
        accuracy=0.80,
        brier=0.10,
        directional_edge=0.25,
        observations=10,
    )

    assert model_stability_component(report) == 30.0


def test_execution_quality_is_capped_when_allocator_rejects() -> None:
    report = GlobalAllocationReport(
        weights=pd.Series({"A": 1.0}),
        cvar=0.10,
        expected_return=0.001,
        turnover=0.50,
        estimated_cost=0.001,
        approved=False,
        reasons=("CVaR limit exceeded",),
    )

    assert execution_quality_component(report) <= 60.0

from __future__ import annotations

from dataclasses import dataclass

from .data_quality import DataQualityReport
from .global_allocator import GlobalAllocationReport
from .model_quality import ModelQuality
from .performance import PerformanceMetrics
from .readiness_score import ReadinessComponents
from .recovery_health import RecoveryHealth
from .reliability import ReliabilityReport
from .robustness import BootstrapReport


@dataclass(frozen=True)
class ReadinessEvidence:
    performance: PerformanceMetrics
    robustness: BootstrapReport
    reliability: ReliabilityReport
    recovery: RecoveryHealth
    data_quality: DataQualityReport
    model_quality: ModelQuality
    execution: GlobalAllocationReport


def _clamp_score(value: float) -> float:
    return max(0.0, min(100.0, float(value)))


def performance_component(metrics: PerformanceMetrics) -> float:
    sharpe = _clamp_score((metrics.sharpe / 2.0) * 100.0)
    sortino = _clamp_score((metrics.sortino / 2.5) * 100.0)
    calmar = _clamp_score((metrics.calmar / 2.0) * 100.0)
    drawdown = _clamp_score((1.0 - metrics.max_drawdown / 0.20) * 100.0)
    return 0.30 * sharpe + 0.25 * sortino + 0.20 * calmar + 0.25 * drawdown


def robustness_component(report: BootstrapReport) -> float:
    positive = _clamp_score(report.probability_positive * 100.0)
    tail = _clamp_score((1.0 - report.probability_loss_gt_10pct) * 100.0)
    p05 = _clamp_score(((report.p05_return + 0.10) / 0.20) * 100.0)
    return 0.45 * positive + 0.35 * tail + 0.20 * p05


def reliability_component(report: ReliabilityReport) -> float:
    return _clamp_score(report.reliability_score)


def recovery_component(report: RecoveryHealth) -> float:
    score = 100.0
    score -= min(60.0, report.recent_failures * 20.0)
    score -= min(40.0, report.max_fallback_depth * 10.0)
    if report.status != "healthy":
        score = min(score, 70.0)
    return _clamp_score(score)


def data_quality_component(report: DataQualityReport) -> float:
    score = report.score * 100.0
    if not report.valid:
        score = min(score, 70.0)
    return _clamp_score(score)


def model_stability_component(report: ModelQuality) -> float:
    score = report.score * 100.0
    if report.observations < 30:
        score *= report.observations / 30.0
    return _clamp_score(score)


def execution_quality_component(report: GlobalAllocationReport) -> float:
    score = 100.0
    score -= min(40.0, report.turnover * 100.0)
    if report.expected_return > 0:
        cost_ratio = report.estimated_cost / report.expected_return
        score -= min(40.0, max(0.0, cost_ratio) * 40.0)
    elif report.estimated_cost > 0:
        score -= 40.0
    if not report.approved:
        score = min(score, 60.0)
    return _clamp_score(score)


def build_readiness_components(evidence: ReadinessEvidence) -> ReadinessComponents:
    return ReadinessComponents(
        performance=performance_component(evidence.performance),
        robustness=robustness_component(evidence.robustness),
        reliability=reliability_component(evidence.reliability),
        recovery=recovery_component(evidence.recovery),
        data_quality=data_quality_component(evidence.data_quality),
        model_stability=model_stability_component(evidence.model_quality),
        execution_quality=execution_quality_component(evidence.execution),
    )

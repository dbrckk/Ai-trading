from __future__ import annotations

from dataclasses import dataclass

from .champions import ChampionRecord, ChampionRegistry
from .drift import DriftReport
from .performance import PerformanceMetrics
from .persistence import ModelStore


@dataclass(frozen=True)
class HealthPolicy:
    min_sharpe: float = 0.0
    max_drawdown: float = 0.15
    rollback_on_drift: bool = True


@dataclass(frozen=True)
class HealthDecision:
    healthy: bool
    rollback: bool
    reason: str


def evaluate_health(
    metrics: PerformanceMetrics,
    drift: DriftReport,
    policy: HealthPolicy | None = None,
) -> HealthDecision:
    policy = policy or HealthPolicy()

    if policy.rollback_on_drift and drift.drifted:
        return HealthDecision(False, True, "distribution drift detected")
    if metrics.sharpe < policy.min_sharpe:
        return HealthDecision(False, True, "Sharpe below health threshold")
    if metrics.max_drawdown > policy.max_drawdown:
        return HealthDecision(False, True, "drawdown above health threshold")
    return HealthDecision(True, False, "healthy")


def rollback_if_needed(
    registry: ChampionRegistry,
    decision: HealthDecision,
    model_store: ModelStore | None = None,
) -> ChampionRecord | None:
    if not decision.rollback:
        return None

    restored = registry.rollback()
    if model_store is not None:
        model_store.activate(restored.version)
    return restored

from __future__ import annotations

from .burnin import BurnInSnapshot, calculate_burnin_metrics
from .mtf_shadow_config import (
    ValidatedMTFShadowConfig,
    validated_mtf_shadow_config,
)
from .paper_readiness_evidence import bootstrap_positive_probability
from .persistence import PaperPersistence, PersistedRuntime
from .readiness import ReadinessPolicy, evaluate_readiness
from .runtime_status import HostedRuntimeStatus, runtime_status_snapshot
from .shadow_promotion_gate import (
    ShadowPromotionPolicy,
    evaluate_shadow_promotion_gate,
)

_MTF_MIN_DIRECTIONAL_OBSERVATIONS = 100


def _empty_model_snapshot() -> dict[str, object]:
    return {
        "present": False,
        "format": None,
        "version": None,
        "checksum": None,
    }


def _empty_shadow_quality_snapshot() -> dict[str, object]:
    policy = ShadowPromotionPolicy()
    return {
        "available": False,
        "status": "collecting",
        "observations": 0,
        "score_delta": None,
        "river": None,
        "challenger": None,
        "promotion_gate": {
            "eligible_for_review": False,
            "min_observations": policy.min_observations,
            "reasons": [
                f"need at least {policy.min_observations} realized shadow observations"
            ],
        },
    }


def _empty_mtf_shadow_quality_snapshot(
    config: ValidatedMTFShadowConfig | None = None,
) -> dict[str, object]:
    policy = ShadowPromotionPolicy(min_observations=500)
    if config is None:
        reasons = ["no benchmark-validated MTF configuration for this market"]
        status = "unvalidated"
        candidate_config = None
        horizon_minutes = None
        label = None
    else:
        reasons = [
            f"need at least {policy.min_observations} realized MTF observations",
            (
                "need at least "
                f"{_MTF_MIN_DIRECTIONAL_OBSERVATIONS} directional MTF observations"
            ),
        ]
        status = "collecting"
        candidate_config = config.as_dict()
        horizon_minutes = config.horizon_minutes
        label = {
            "type": "volatility_adaptive",
            "minimum_threshold": config.minimum_threshold,
            "atr_multiplier": config.atr_multiplier,
        }
    return {
        "available": False,
        "status": status,
        "candidate_config": candidate_config,
        "observations": 0,
        "directional_observations": 0,
        "directional_rate": 0.0,
        "label_distribution": {"long": 0, "flat": 0, "short": 0},
        "score_delta": None,
        "river": None,
        "challenger": None,
        "horizon_minutes": horizon_minutes,
        "timeframes": ["5m", "15m", "1h", "4h"],
        "label": label,
        "promotion_gate": {
            "eligible_for_review": False,
            "min_observations": policy.min_observations,
            "min_directional_observations": _MTF_MIN_DIRECTIONAL_OBSERVATIONS,
            "reasons": reasons,
        },
    }


def _shadow_quality_snapshot(comparison) -> dict[str, object]:
    observations = int(comparison.observations)
    available = observations >= 5

    def quality_payload(quality) -> dict[str, object]:
        return {
            "score": float(quality.score),
            "accuracy": float(quality.accuracy),
            "brier": float(quality.brier),
            "directional_edge": float(quality.directional_edge),
            "observations": int(quality.observations),
        }

    policy = ShadowPromotionPolicy()
    gate = evaluate_shadow_promotion_gate(comparison, policy)
    return {
        "available": available,
        "status": "comparable" if available else "collecting",
        "candidate_config": config.as_dict(),
        "observations": observations,
        "score_delta": float(comparison.score_delta) if available else None,
        "river": quality_payload(comparison.river) if observations else None,
        "challenger": quality_payload(comparison.challenger) if observations else None,
        "promotion_gate": {
            "eligible_for_review": gate.eligible_for_review,
            "min_observations": policy.min_observations,
            "reasons": list(gate.reasons),
            "score_delta": gate.score_delta,
            "accuracy_delta": gate.accuracy_delta,
            "brier_delta": gate.brier_delta,
            "directional_edge_delta": gate.directional_edge_delta,
        },
    }


def _mtf_shadow_quality_snapshot(
    comparison,
    config: ValidatedMTFShadowConfig,
) -> dict[str, object]:
    observations = int(comparison.observations)
    available = observations >= 5

    def quality_payload(quality) -> dict[str, object]:
        return {
            "score": float(quality.score),
            "accuracy": float(quality.accuracy),
            "brier": float(quality.brier),
            "directional_edge": float(quality.directional_edge),
            "observations": int(quality.observations),
        }

    policy = ShadowPromotionPolicy(min_observations=500)
    gate = evaluate_shadow_promotion_gate(comparison, policy)
    directional_observations = int(comparison.directional_observations)
    directional_rate = float(comparison.directional_rate)
    gate_reasons = list(gate.reasons)
    if directional_observations < _MTF_MIN_DIRECTIONAL_OBSERVATIONS:
        gate_reasons.append(
            "need at least "
            f"{_MTF_MIN_DIRECTIONAL_OBSERVATIONS} directional MTF observations"
        )
    eligible_for_review = gate.eligible_for_review and not gate_reasons
    return {
        "available": available,
        "status": "comparable" if available else "collecting",
        "observations": observations,
        "directional_observations": directional_observations,
        "directional_rate": directional_rate,
        "label_distribution": {
            "long": int(comparison.long_labels),
            "flat": int(comparison.flat_labels),
            "short": int(comparison.short_labels),
        },
        "score_delta": float(comparison.score_delta) if available else None,
        "river": quality_payload(comparison.river) if observations else None,
        "challenger": quality_payload(comparison.challenger) if observations else None,
        "horizon_minutes": config.horizon_minutes,
        "timeframes": ["5m", "15m", "1h", "4h"],
        "label": {
            "type": "volatility_adaptive",
            "minimum_threshold": config.minimum_threshold,
            "atr_multiplier": config.atr_multiplier,
        },
        "promotion_gate": {
            "eligible_for_review": eligible_for_review,
            "min_observations": policy.min_observations,
            "min_directional_observations": _MTF_MIN_DIRECTIONAL_OBSERVATIONS,
            "reasons": gate_reasons,
            "score_delta": gate.score_delta,
            "accuracy_delta": gate.accuracy_delta,
            "brier_delta": gate.brier_delta,
            "directional_edge_delta": gate.directional_edge_delta,
        },
    }


def runtime_is_consistent(persisted: PersistedRuntime) -> bool:
    state = persisted.state
    if persisted.is_new:
        return (
            persisted.revision == 0
            and persisted.model is None
            and state.processed_bars == 0
            and not state.last_processed
            and state.units == 0.0
            and state.last_price == 0.0
        )
    if persisted.revision < 0 or state.processed_bars < 0:
        return False
    if state.processed_bars > 0 and not state.last_processed:
        return False
    return state.units == 0.0 or state.last_price > 0.0


def _burnin_snapshot(snapshots: tuple[BurnInSnapshot, ...]) -> dict[str, object]:
    latest_bars = snapshots[-1].processed_bars if snapshots else 0
    if len(snapshots) < 2:
        return {
            "samples": len(snapshots),
            "processed_bars": latest_bars,
            "total_return": None,
            "max_drawdown": None,
        }
    metrics = calculate_burnin_metrics(snapshots)
    return {
        "samples": len(snapshots),
        "processed_bars": latest_bars,
        "total_return": metrics.total_return,
        "max_drawdown": metrics.max_drawdown,
    }



def _empty_readiness_snapshot() -> dict[str, object]:
    return {
        "available": False,
        "ready": None,
        "checks_passed": None,
        "checks_total": 8,
        "checks": [],
    }


def _readiness_snapshot(
    snapshots: tuple[BurnInSnapshot, ...],
    regimes: tuple[str, ...],
    status: HostedRuntimeStatus | None,
) -> dict[str, object]:
    if len(snapshots) < 3 or status is None:
        return _empty_readiness_snapshot()
    metrics = calculate_burnin_metrics(snapshots)
    probability = bootstrap_positive_probability(
        tuple(float(snapshot.equity) for snapshot in snapshots)
    )
    if probability is None:
        return _empty_readiness_snapshot()
    report = evaluate_readiness(
        metrics=metrics,
        burn_in_bars=snapshots[-1].processed_bars,
        bootstrap_probability_positive=probability,
        regimes_covered=len(regimes),
        scheduler_errors=status.consecutive_cycle_errors,
        policy=ReadinessPolicy(),
    )
    return {
        "available": True,
        "ready": report.ready,
        "checks_passed": report.checks_passed,
        "checks_total": report.checks_total,
        "checks": [
            {
                "name": check.name,
                "passed": check.passed,
                "value": check.value,
                "threshold": check.threshold,
                "comparison": check.comparison,
            }
            for check in report.checks
        ],
    }


def build_operational_overview(
    persistence: PaperPersistence,
    runtime_key: str,
    starting_cash: float = 100_000.0,
) -> dict[str, object]:
    runtime_parts = runtime_key.split(":", 2)
    runtime_symbol = runtime_parts[1] if len(runtime_parts) > 1 else ""
    mtf_config = validated_mtf_shadow_config(runtime_symbol)
    try:
        persisted = persistence.load_runtime(runtime_key, starting_cash)
        status = persistence.load_runtime_status(runtime_key)
        burnin_loader = getattr(persistence, "list_burnin_snapshots", None)
        snapshots = (
            tuple(burnin_loader(runtime_key))
            if callable(burnin_loader)
            else ()
        )
        regime_loader = getattr(persistence, "list_regimes", None)
        regimes = tuple(regime_loader(runtime_key)) if callable(regime_loader) else ()
        burnin = _burnin_snapshot(snapshots)
        readiness = _readiness_snapshot(snapshots, regimes, status)
    except Exception:  # noqa: BLE001 - observability boundary must sanitize backend failures
        return {
            "storage_healthy": False,
            "engine_status": "ERROR",
            "runtime_revision": None,
            "processed_bars": None,
            "last_processed": None,
            "lag_detected": False,
            "consecutive_cycle_errors": None,
            "model": _empty_model_snapshot(),
            "burnin": {
                "samples": 0,
                "processed_bars": 0,
                "total_return": None,
                "max_drawdown": None,
            },
            "readiness": _empty_readiness_snapshot(),
            "shadow_challenger": _empty_shadow_quality_snapshot(),
            "mtf_shadow_challenger": _empty_mtf_shadow_quality_snapshot(mtf_config),
            "alerts": ["storage unavailable"],
        }

    shadow_quality = _empty_shadow_quality_snapshot()
    shadow_loader = getattr(persistence, "load_shadow_quality", None)
    if callable(shadow_loader):
        try:
            shadow_quality = _shadow_quality_snapshot(shadow_loader(runtime_key))
        except Exception:  # noqa: BLE001 - optional observability must not break runtime status
            shadow_quality = _empty_shadow_quality_snapshot()

    mtf_shadow_quality = _empty_mtf_shadow_quality_snapshot(mtf_config)
    mtf_shadow_loader = getattr(persistence, "load_mtf_shadow_quality", None)
    if mtf_config is not None and callable(mtf_shadow_loader):
        try:
            mtf_shadow_quality = _mtf_shadow_quality_snapshot(
                mtf_shadow_loader(
                    runtime_key,
                    config_name=mtf_config.config_name,
                ),
                mtf_config,
            )
        except Exception:  # noqa: BLE001 - optional observer must not break status
            mtf_shadow_quality = _empty_mtf_shadow_quality_snapshot(mtf_config)

    status_snapshot = runtime_status_snapshot(status)
    engine_status = str(status_snapshot["engine_status"])
    lag_detected = engine_status == "STALE"
    consecutive_cycle_errors = (
        status.consecutive_cycle_errors if status is not None else 0
    )
    state = persisted.state
    model = persisted.model

    alerts: list[str] = []
    if lag_detected:
        alerts.append("worker heartbeat expired")
    if consecutive_cycle_errors > 0:
        alerts.append("paper cycle reliability degraded")
    if model is None and state.processed_bars > 0:
        alerts.append("model missing for initialized runtime")
    if not runtime_is_consistent(persisted):
        alerts.append("runtime inconsistent")

    model_snapshot: dict[str, object]
    if model is None:
        model_snapshot = _empty_model_snapshot()
    else:
        model_snapshot = {
            "present": True,
            "format": model.format,
            "version": model.version,
            "checksum": model.sha256[:12],
        }

    return {
        "storage_healthy": True,
        "engine_status": engine_status,
        "runtime_revision": persisted.revision,
        "processed_bars": state.processed_bars,
        "last_processed": state.last_processed,
        "lag_detected": lag_detected,
        "consecutive_cycle_errors": consecutive_cycle_errors,
        "model": model_snapshot,
        "burnin": burnin,
        "readiness": readiness,
        "shadow_challenger": shadow_quality,
        "mtf_shadow_challenger": mtf_shadow_quality,
        "alerts": alerts,
    }

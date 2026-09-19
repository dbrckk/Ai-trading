from __future__ import annotations

from .burnin import BurnInSnapshot, calculate_burnin_metrics
from .paper_readiness_evidence import bootstrap_positive_probability
from .persistence import PaperPersistence, PersistedRuntime
from .readiness import ReadinessPolicy, evaluate_readiness
from .runtime_status import HostedRuntimeStatus, runtime_status_snapshot
from .shadow_quality import ShadowQualityReport, evaluate_shadow_quality


def _empty_model_snapshot() -> dict[str, object]:
    return {
        "present": False,
        "format": None,
        "version": None,
        "checksum": None,
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





def _shadow_quality_snapshot(report: ShadowQualityReport) -> dict[str, object]:
    return {
        "observations": report.observations,
        "agreement_rate": report.agreement_rate,
        "accuracy_delta": report.accuracy_delta,
        "brier_improvement": report.brier_improvement,
        "regimes": list(report.regimes),
        "active": {
            "accuracy": report.active.accuracy,
            "brier": report.active.brier,
            "directional_edge": report.active.directional_edge,
            "directional_observations": report.active.directional_observations,
        },
        "challenger": {
            "accuracy": report.challenger.accuracy,
            "brier": report.challenger.brier,
            "directional_edge": report.challenger.directional_edge,
            "directional_observations": report.challenger.directional_observations,
        },
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
        shadow_loader = getattr(persistence, "list_shadow_observations", None)
        shadow_observations = (
            tuple(shadow_loader(runtime_key))
            if callable(shadow_loader)
            else ()
        )
        shadow_quality = _shadow_quality_snapshot(
            evaluate_shadow_quality(shadow_observations)
        )
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
            "shadow_challenger": _shadow_quality_snapshot(
                evaluate_shadow_quality(())
            ),
            "alerts": ["storage unavailable"],
        }

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
        "alerts": alerts,
    }

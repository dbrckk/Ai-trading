from __future__ import annotations

from .persistence import PaperPersistence, PersistedRuntime
from .runtime_status import runtime_status_snapshot


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


def build_operational_overview(
    persistence: PaperPersistence,
    runtime_key: str,
    starting_cash: float = 100_000.0,
) -> dict[str, object]:
    try:
        persisted = persistence.load_runtime(runtime_key, starting_cash)
        status = persistence.load_runtime_status(runtime_key)
    except Exception:  # noqa: BLE001 - observability boundary must sanitize backend failures
        return {
            "storage_healthy": False,
            "engine_status": "ERROR",
            "runtime_revision": None,
            "processed_bars": None,
            "last_processed": None,
            "lag_detected": False,
            "model": _empty_model_snapshot(),
            "alerts": ["storage unavailable"],
        }

    status_snapshot = runtime_status_snapshot(status)
    engine_status = str(status_snapshot["engine_status"])
    lag_detected = engine_status == "STALE"
    state = persisted.state
    model = persisted.model

    alerts: list[str] = []
    if lag_detected:
        alerts.append("worker heartbeat expired")
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
        "model": model_snapshot,
        "alerts": alerts,
    }

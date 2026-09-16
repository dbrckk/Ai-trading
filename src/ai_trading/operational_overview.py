from __future__ import annotations

from .persistence import PersistedRuntime
from .runtime_status import HostedRuntimeStatus, runtime_status_snapshot


def _runtime_consistent(runtime: PersistedRuntime) -> bool:
    state = runtime.state
    if runtime.is_new:
        return (
            runtime.revision == 0
            and runtime.model is None
            and state.processed_bars == 0
            and not state.last_processed
            and state.units == 0.0
            and state.last_price == 0.0
        )
    if runtime.revision < 0 or state.processed_bars < 0:
        return False
    if state.processed_bars > 0 and not state.last_processed:
        return False
    if state.units != 0.0 and state.last_price <= 0.0:
        return False
    return True


def build_operational_overview(
    runtime: PersistedRuntime,
    status: HostedRuntimeStatus | None,
) -> dict[str, object]:
    model = runtime.model
    snapshot = runtime_status_snapshot(status)
    engine_status = str(snapshot["engine_status"])
    consistent = _runtime_consistent(runtime)

    alerts: list[str] = []
    if engine_status == "STALE":
        alerts.append("worker heartbeat expired")
    if model is None and not runtime.is_new:
        alerts.append("model missing")
    if not consistent:
        alerts.append("runtime inconsistent")

    return {
        "runtime": {
            "revision": runtime.revision,
            "is_new": runtime.is_new,
            "processed_bars": runtime.state.processed_bars,
            "last_processed": runtime.state.last_processed,
            "consistent": consistent,
        },
        "model": {
            "present": model is not None,
            "format": None if model is None else model.format,
            "version": None if model is None else model.version,
            "sha256_short": None if model is None else model.sha256[:12],
        },
        "sync": {
            "engine_status": engine_status,
            "lag_detected": engine_status == "STALE",
        },
        "alerts": alerts,
    }

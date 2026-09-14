from __future__ import annotations

from dataclasses import dataclass

from .control_plane import read_control_plane
from .governor_state_store import GovernorStateStore
from .supervisor_state import SupervisorStateStore
from .watchdog import HeartbeatStore, heartbeat_is_stale


@dataclass(frozen=True)
class MetricsSnapshot:
    governor_trade: int
    governor_halt: int
    heartbeat_stale: int
    crisis_level: int
    consecutive_halts: int
    supervisor_running: int
    supervisor_restarting: int
    supervisor_maintenance: int
    supervisor_halted: int
    supervisor_restarts: int


def collect_metrics(
    *,
    heartbeat_store: HeartbeatStore | None = None,
    governor_store: GovernorStateStore | None = None,
    supervisor_store: SupervisorStateStore | None = None,
) -> MetricsSnapshot:
    heartbeat_store = heartbeat_store or HeartbeatStore(
        "artifacts/multiasset_heartbeat.json"
    )
    governor_store = governor_store or GovernorStateStore()
    supervisor_store = supervisor_store or SupervisorStateStore()
    control = read_control_plane(governor_store=governor_store)
    governor = governor_store.load()
    supervisor = supervisor_store.load()

    crisis_levels = {
        "normal": 0,
        "cautious": 1,
        "defensive": 2,
        "capital-preservation": 3,
    }

    return MetricsSnapshot(
        governor_trade=int(control.governor_verdict == "TRADE"),
        governor_halt=int(control.governor_verdict == "HALT"),
        heartbeat_stale=int(heartbeat_is_stale(heartbeat_store.load())),
        crisis_level=crisis_levels.get(control.crisis_mode, 99),
        consecutive_halts=governor.consecutive_halts,
        supervisor_running=int(supervisor.status == "running"),
        supervisor_restarting=int(supervisor.status == "restarting"),
        supervisor_maintenance=int(supervisor.status == "maintenance"),
        supervisor_halted=int(supervisor.status == "halted"),
        supervisor_restarts=supervisor.restarts,
    )


def prometheus_text(snapshot: MetricsSnapshot) -> str:
    return "\n".join(
        [
            "# TYPE ai_trading_governor_trade gauge",
            f"ai_trading_governor_trade {snapshot.governor_trade}",
            "# TYPE ai_trading_governor_halt gauge",
            f"ai_trading_governor_halt {snapshot.governor_halt}",
            "# TYPE ai_trading_heartbeat_stale gauge",
            f"ai_trading_heartbeat_stale {snapshot.heartbeat_stale}",
            "# TYPE ai_trading_crisis_level gauge",
            f"ai_trading_crisis_level {snapshot.crisis_level}",
            "# TYPE ai_trading_consecutive_halts gauge",
            f"ai_trading_consecutive_halts {snapshot.consecutive_halts}",
            "# TYPE ai_trading_supervisor_running gauge",
            f"ai_trading_supervisor_running {snapshot.supervisor_running}",
            "# TYPE ai_trading_supervisor_restarting gauge",
            f"ai_trading_supervisor_restarting {snapshot.supervisor_restarting}",
            "# TYPE ai_trading_supervisor_maintenance gauge",
            f"ai_trading_supervisor_maintenance {snapshot.supervisor_maintenance}",
            "# TYPE ai_trading_supervisor_halted gauge",
            f"ai_trading_supervisor_halted {snapshot.supervisor_halted}",
            "# TYPE ai_trading_supervisor_restarts gauge",
            f"ai_trading_supervisor_restarts {snapshot.supervisor_restarts}",
            "",
        ]
    )

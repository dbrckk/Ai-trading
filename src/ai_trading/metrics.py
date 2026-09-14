from __future__ import annotations

from dataclasses import dataclass

from .control_plane import read_control_plane
from .governor_state_store import GovernorStateStore
from .lifecycle_log import LifecycleEventLog
from .model_quarantine import ModelQuarantineStore
from .recovery_health import evaluate_recovery_health
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
    promotion_total: int
    promotion_rejected_total: int
    rollback_total: int
    quarantine_total: int
    recovery_attempt_total: int
    recovery_success_total: int
    recovery_failure_total: int
    recovery_fallback_depth: int
    recovery_degraded: int


def collect_metrics(
    *,
    heartbeat_store: HeartbeatStore | None = None,
    governor_store: GovernorStateStore | None = None,
    supervisor_store: SupervisorStateStore | None = None,
    lifecycle_log: LifecycleEventLog | None = None,
    quarantine_store: ModelQuarantineStore | None = None,
) -> MetricsSnapshot:
    heartbeat_store = heartbeat_store or HeartbeatStore(
        "artifacts/multiasset_heartbeat.json"
    )
    governor_store = governor_store or GovernorStateStore()
    supervisor_store = supervisor_store or SupervisorStateStore()
    lifecycle_log = lifecycle_log or LifecycleEventLog()
    quarantine_store = quarantine_store or ModelQuarantineStore()
    control = read_control_plane(governor_store=governor_store)
    governor = governor_store.load()
    supervisor = supervisor_store.load()
    lifecycle_events = lifecycle_log.list()
    quarantine_records = quarantine_store.load()
    recovery_health = evaluate_recovery_health(lifecycle_log)

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
        promotion_total=sum(event.event == "promotion" for event in lifecycle_events),
        promotion_rejected_total=sum(
            event.event == "promotion_rejected" for event in lifecycle_events
        ),
        rollback_total=sum(event.event == "rollback" for event in lifecycle_events),
        quarantine_total=sum(record.quarantined for record in quarantine_records.values()),
        recovery_attempt_total=sum(
            event.event in {"recovery_succeeded", "recovery_failed"}
            for event in lifecycle_events
        ),
        recovery_success_total=sum(
            event.event == "recovery_succeeded" for event in lifecycle_events
        ),
        recovery_failure_total=sum(
            event.event == "recovery_failed" for event in lifecycle_events
        ),
        recovery_fallback_depth=max(
            (
                int(event.metadata.get("fallback_depth", 0))
                for event in lifecycle_events
                if event.event in {"recovery_succeeded", "recovery_failed"}
            ),
            default=0,
        ),
        recovery_degraded=int(recovery_health.status == "degraded"),
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
            "# TYPE ai_trading_promotion_total counter",
            f"ai_trading_promotion_total {snapshot.promotion_total}",
            "# TYPE ai_trading_promotion_rejected_total counter",
            f"ai_trading_promotion_rejected_total {snapshot.promotion_rejected_total}",
            "# TYPE ai_trading_rollback_total counter",
            f"ai_trading_rollback_total {snapshot.rollback_total}",
            "# TYPE ai_trading_quarantine_total gauge",
            f"ai_trading_quarantine_total {snapshot.quarantine_total}",
            "# TYPE ai_trading_recovery_attempt_total counter",
            f"ai_trading_recovery_attempt_total {snapshot.recovery_attempt_total}",
            "# TYPE ai_trading_recovery_success_total counter",
            f"ai_trading_recovery_success_total {snapshot.recovery_success_total}",
            "# TYPE ai_trading_recovery_failure_total counter",
            f"ai_trading_recovery_failure_total {snapshot.recovery_failure_total}",
            "# TYPE ai_trading_recovery_fallback_depth gauge",
            f"ai_trading_recovery_fallback_depth {snapshot.recovery_fallback_depth}",
            "# TYPE ai_trading_recovery_degraded gauge",
            f"ai_trading_recovery_degraded {snapshot.recovery_degraded}",
            "",
        ]
    )

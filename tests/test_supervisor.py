import json
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path

from ai_trading.lifecycle_log import LifecycleEventLog
from ai_trading.maintenance import MaintenanceState, MaintenanceStore
from ai_trading.qualification_store import QualificationRecord, QualificationStore
from ai_trading.resilience import ResilienceState, ResilienceStateStore
from ai_trading.supervisor import PaperSupervisor, SupervisorConfig
from ai_trading.supervisor_lease import SupervisorLeaseStore


def test_supervisor_stops_for_maintenance_before_worker_start(tmp_path: Path) -> None:
    maintenance = MaintenanceStore(tmp_path / "maintenance.json")
    maintenance.save(MaintenanceState(enabled=True, reason="upgrade"))

    supervisor = PaperSupervisor(
        command=["python", "-c", "raise SystemExit(1)"],
        state_files=[],
        audit_path=tmp_path / "audit.jsonl",
        config=SupervisorConfig(max_restarts=1),
        lease_store=SupervisorLeaseStore(tmp_path / "lease.json"),
        maintenance_store=maintenance,
    )

    result = supervisor.run()
    assert result.stopped_for_maintenance
    assert result.restarts == 0



def test_supervisor_does_not_start_worker_when_resilience_halted(
    tmp_path: Path,
) -> None:
    resilience = ResilienceStateStore(tmp_path / "resilience.json")
    resilience.save(ResilienceState(mode="HALT", reason="critical"))

    supervisor = PaperSupervisor(
        command=["python", "-c", "raise SystemExit(0)"],
        state_files=[],
        audit_path=tmp_path / "audit.jsonl",
        config=SupervisorConfig(max_restarts=1),
        lease_store=SupervisorLeaseStore(tmp_path / "lease.json"),
        resilience_store=resilience,
    )

    result = supervisor.run()

    assert result.restarts == 0
    assert not result.stopped_for_maintenance


def test_supervisor_treats_resilience_cooldown_as_maintenance(
    tmp_path: Path,
) -> None:
    resilience = ResilienceStateStore(tmp_path / "resilience.json")
    resilience.save(ResilienceState(mode="COOLDOWN", reason="stabilizing"))

    supervisor = PaperSupervisor(
        command=["python", "-c", "raise SystemExit(0)"],
        state_files=[],
        audit_path=tmp_path / "audit.jsonl",
        config=SupervisorConfig(max_restarts=1),
        lease_store=SupervisorLeaseStore(tmp_path / "lease.json"),
        resilience_store=resilience,
    )

    result = supervisor.run()

    assert result.restarts == 0
    assert result.stopped_for_maintenance



def test_supervisor_blocks_qualified_soak_when_reliability_sla_fails(
    tmp_path: Path,
) -> None:
    qualification_store = QualificationStore(tmp_path / "qualification.json")
    record = QualificationRecord(
        created_at_utc=datetime.now(UTC).isoformat(),
        passed=True,
        success_ratio=1.0,
        reasons=(),
        cycles=100,
        failures=0,
        max_drawdown=0.01,
        governor_verdict="TRADE",
        crisis_mode="normal",
        symbols=("GC=F",),
        period="2y",
        interval="1d",
    )
    qualification_store.path.write_text(
        json.dumps(asdict(record), sort_keys=True),
        encoding="utf-8",
    )
    resilience = ResilienceStateStore(tmp_path / "resilience.json")
    resilience.save(
        ResilienceState(
            mode="DEGRADED",
            reason="persistent instability",
            mode_steps=20,
            instability_status="degraded",
        )
    )

    supervisor = PaperSupervisor(
        command=["python", "-c", "raise SystemExit(0)"],
        state_files=[],
        audit_path=tmp_path / "audit.jsonl",
        config=SupervisorConfig(
            max_restarts=1,
            require_qualification=True,
            require_reliability_qualification=True,
            qualification_symbols=("GC=F",),
            qualification_period="2y",
            qualification_interval="1d",
        ),
        lease_store=SupervisorLeaseStore(tmp_path / "lease.json"),
        qualification_store=qualification_store,
        resilience_store=resilience,
        lifecycle_log=LifecycleEventLog(tmp_path / "lifecycle.jsonl"),
    )

    result = supervisor.run()

    assert result.restarts == 0
    assert not result.stopped_for_maintenance

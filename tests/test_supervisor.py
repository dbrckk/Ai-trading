from pathlib import Path

from ai_trading.maintenance import MaintenanceState, MaintenanceStore
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

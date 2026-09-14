from pathlib import Path

from ai_trading.maintenance import MaintenanceState, MaintenanceStore
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

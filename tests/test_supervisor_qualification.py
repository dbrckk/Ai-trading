from pathlib import Path

from ai_trading.governor_state_store import GovernorStateStore
from ai_trading.maintenance import MaintenanceStore
from ai_trading.qualification_store import QualificationStore
from ai_trading.supervisor import PaperSupervisor, SupervisorConfig
from ai_trading.supervisor_lease import SupervisorLeaseStore


def test_supervisor_requires_passing_qualification_when_enabled(tmp_path: Path) -> None:
    governor = GovernorStateStore(tmp_path / "governor.json")
    supervisor = PaperSupervisor(
        command=["python", "-c", "raise SystemExit(0)"],
        state_files=[],
        audit_path=tmp_path / "audit.jsonl",
        config=SupervisorConfig(
            max_restarts=0,
            require_qualification=True,
        ),
        lease_store=SupervisorLeaseStore(tmp_path / "lease.json"),
        maintenance_store=MaintenanceStore(tmp_path / "maintenance.json"),
        governor_store=governor,
        qualification_store=QualificationStore(tmp_path / "missing.json"),
    )

    result = supervisor.run()
    assert result.final_exit_code is None
    assert governor.load().verdict == "HALT"

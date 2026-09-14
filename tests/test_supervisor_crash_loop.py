from pathlib import Path

from ai_trading.governor_state_store import GovernorStateStore
from ai_trading.maintenance import MaintenanceStore
from ai_trading.restart_log import RestartLog
from ai_trading.supervisor import PaperSupervisor, SupervisorConfig
from ai_trading.supervisor_lease import SupervisorLeaseStore


def test_supervisor_crash_loop_halts_governor(tmp_path: Path) -> None:
    governor = GovernorStateStore(tmp_path / "governor.json")
    supervisor = PaperSupervisor(
        command=["python", "-c", "raise SystemExit(1)"],
        state_files=[],
        audit_path=tmp_path / "audit.jsonl",
        config=SupervisorConfig(
            max_restarts=5,
            crash_window_seconds=60.0,
            max_crashes_in_window=2,
            initial_backoff_seconds=0.0,
            max_backoff_seconds=0.0,
        ),
        lease_store=SupervisorLeaseStore(tmp_path / "lease.json"),
        maintenance_store=MaintenanceStore(tmp_path / "maintenance.json"),
        restart_log=RestartLog(tmp_path / "restarts.jsonl"),
        governor_store=governor,
    )

    result = supervisor.run()
    assert result.crash_loop_detected
    assert governor.load().verdict == "HALT"

from pathlib import Path

from ai_trading.supervisor_state import SupervisorStateStore


def test_supervisor_state_round_trip(tmp_path: Path) -> None:
    store = SupervisorStateStore(tmp_path / "supervisor.json")
    state = store.save(
        status="running",
        worker_pid=123,
        restarts=2,
        reason="ok",
    )
    assert store.load() == state
    assert state.worker_pid == 123

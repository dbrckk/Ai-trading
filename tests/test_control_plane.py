from pathlib import Path

from ai_trading.control_plane import read_control_plane
from ai_trading.crisis_controller import CrisisState
from ai_trading.crisis_state_store import CrisisStateStore
from ai_trading.governor_state_store import GovernorState, GovernorStateStore


def test_control_plane_halts_scheduler_on_governor_halt(tmp_path: Path) -> None:
    governor = GovernorStateStore(tmp_path / "governor.json")
    crisis = CrisisStateStore(tmp_path / "crisis.json")
    governor.save(GovernorState(verdict="HALT", reason="bad data"))
    crisis.save(CrisisState(mode="defensive"))

    status = read_control_plane(
        governor_store=governor,
        crisis_store=crisis,
    )
    assert not status.scheduler_should_run
    assert not status.promotions_allowed

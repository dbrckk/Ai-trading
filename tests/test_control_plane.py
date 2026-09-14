from pathlib import Path

from ai_trading.control_plane import read_control_plane
from ai_trading.crisis_controller import CrisisState
from ai_trading.crisis_state_store import CrisisStateStore
from ai_trading.governor_state_store import GovernorState, GovernorStateStore
from ai_trading.lifecycle_log import LifecycleEventLog


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



def test_control_plane_blocks_promotions_when_recovery_is_degraded(
    tmp_path: Path,
) -> None:
    governor = GovernorStateStore(tmp_path / "governor.json")
    crisis = CrisisStateStore(tmp_path / "crisis.json")
    lifecycle = LifecycleEventLog(tmp_path / "lifecycle.jsonl")
    governor.save(GovernorState(verdict="TRADE", reason="ok"))
    crisis.save(CrisisState(mode="normal"))
    lifecycle.append(
        event="recovery_failed",
        version="",
        model_name="",
        failure_type="technical_failure",
        metadata={"fallback_depth": 4},
    )

    status = read_control_plane(
        governor_store=governor,
        crisis_store=crisis,
        lifecycle_log=lifecycle,
    )

    assert status.scheduler_should_run
    assert not status.promotions_allowed

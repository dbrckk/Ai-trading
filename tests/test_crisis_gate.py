from pathlib import Path

from ai_trading.crisis_controller import CrisisState
from ai_trading.crisis_gate import promotions_allowed
from ai_trading.crisis_state_store import CrisisStateStore
from ai_trading.governor_state_store import GovernorState, GovernorStateStore


def test_promotions_are_frozen_outside_normal_mode(tmp_path: Path) -> None:
    crisis = CrisisStateStore(tmp_path / "crisis.json")
    governor = GovernorStateStore(tmp_path / "governor.json")
    assert promotions_allowed(crisis, governor)

    crisis.save(CrisisState(mode="defensive"))
    assert not promotions_allowed(crisis, governor)


def test_governor_freeze_blocks_promotions(tmp_path: Path) -> None:
    crisis = CrisisStateStore(tmp_path / "crisis.json")
    governor = GovernorStateStore(tmp_path / "governor.json")
    governor.save(GovernorState(verdict="FREEZE", reason="risk gate failed"))
    assert not promotions_allowed(crisis, governor)

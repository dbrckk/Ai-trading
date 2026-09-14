from pathlib import Path

from ai_trading.crisis_controller import CrisisState
from ai_trading.crisis_gate import promotions_allowed
from ai_trading.crisis_state_store import CrisisStateStore


def test_promotions_are_frozen_outside_normal_mode(tmp_path: Path) -> None:
    store = CrisisStateStore(tmp_path / "crisis.json")
    assert promotions_allowed(store)

    store.save(CrisisState(mode="defensive"))
    assert not promotions_allowed(store)

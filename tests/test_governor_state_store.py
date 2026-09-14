from pathlib import Path

from ai_trading.governor_state_store import GovernorState, GovernorStateStore


def test_governor_state_store_round_trip(tmp_path: Path) -> None:
    store = GovernorStateStore(tmp_path / "governor.json")
    state = GovernorState(verdict="FREEZE", reason="test", consecutive_halts=2)
    store.save(state)
    assert store.load() == state

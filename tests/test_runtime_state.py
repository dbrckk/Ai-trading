from pathlib import Path

from ai_trading.runtime_state import RuntimeState, RuntimeStateStore


def test_runtime_state_round_trip(tmp_path: Path) -> None:
    store = RuntimeStateStore(tmp_path / "state.json")
    state = RuntimeState(
        cash=99_000.0,
        units=2.0,
        last_price=100.0,
        peak_equity=100_100.0,
        day_start_equity=100_000.0,
        last_processed="2026-01-01",
        processed_bars=5,
        last_learning_cycle_bar=0,
    )
    store.save(state)
    assert store.load(100_000.0) == state

from pathlib import Path

from ai_trading.multiasset_state import AssetPosition, MultiAssetState, MultiAssetStateStore


def test_multiasset_state_round_trip(tmp_path: Path) -> None:
    store = MultiAssetStateStore(tmp_path / "state.json")
    state = MultiAssetState(
        cash=80_000.0,
        peak_equity=101_000.0,
        day_start_equity=100_000.0,
        positions={
            "A": AssetPosition(units=10.0, last_price=100.0),
            "B": AssetPosition(units=5.0, last_price=200.0),
        },
        last_processed="2026-01-01",
        processed_bars=5,
    )
    store.save(state)
    loaded = store.load(100_000.0)
    assert loaded == state
    assert loaded.equity() == 82_000.0

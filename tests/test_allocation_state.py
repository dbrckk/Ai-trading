from pathlib import Path

import pandas as pd

from ai_trading.allocation_state import AllocationStateStore


def test_allocation_state_round_trip(tmp_path: Path) -> None:
    store = AllocationStateStore(tmp_path / "allocation.json")
    weights = pd.Series({"A|x|r": 0.4, "B|y|r": 0.6})
    store.save(weights)
    loaded = store.load()
    assert loaded.to_dict() == weights.to_dict()

from pathlib import Path

from ai_trading.persistence import ModelStore


def test_active_model_pointer_round_trip(tmp_path: Path) -> None:
    store = ModelStore(tmp_path / "models")
    store.save("v1", {"id": 1})
    store.save("v2", {"id": 2})

    store.activate("v1")
    assert store.active_name() == "v1"
    assert store.load_active_model() == {"id": 1}

    store.activate("v2")
    assert store.active_name() == "v2"
    assert store.load_active_model() == {"id": 2}

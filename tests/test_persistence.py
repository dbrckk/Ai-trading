from pathlib import Path

from ai_trading.persistence import ModelStore


def test_model_store_round_trip(tmp_path: Path) -> None:
    store = ModelStore(tmp_path / "models")
    model = {"weights": [1, 2, 3]}
    saved = store.save("champion", model, {"version": "v1"})
    assert saved.path.exists()
    assert store.load("champion").metadata["version"] == "v1"
    assert store.load_model("champion") == model

import json
from dataclasses import asdict
from pathlib import Path

from ai_trading.multiasset_checkpoint import MultiAssetCheckpointStore
from ai_trading.multiasset_state import MultiAssetState


def _state(step: int) -> MultiAssetState:
    return MultiAssetState(
        cash=1000.0,
        peak_equity=1000.0,
        day_start_equity=1000.0,
        last_processed=f"bar-{step}",
        processed_bars=step,
    )


def test_checkpoint_ignores_truncated_newer_unpublished_model(tmp_path: Path) -> None:
    store = MultiAssetCheckpointStore(tmp_path / "checkpoint")
    store.commit(_state(3), {"A": {"learned": 3}})

    orphan = store.root / "step-000000000004"
    orphan.mkdir()
    state_path = orphan / "state.json"
    state_path.write_text(
        json.dumps(asdict(_state(4)), sort_keys=True),
        encoding="utf-8",
    )
    model_path = orphan / "model.joblib"
    model_path.write_bytes(b"")
    manifest = {
        "generation": orphan.name,
        "processed_bars": 4,
        "last_processed": "bar-4",
        "state": {
            "file": state_path.name,
            "sha256": store._sha256(state_path),
        },
        "models": {
            "A": {
                "file": model_path.name,
                "sha256": store._sha256(model_path),
            }
        },
    }
    (orphan / "manifest.json").write_text(
        json.dumps(manifest, sort_keys=True),
        encoding="utf-8",
    )

    loaded = store.load()

    assert loaded is not None
    loaded_state, models = loaded
    assert loaded_state.processed_bars == 3
    assert models == {"A": {"learned": 3}}
    assert store.current_path.read_text(encoding="utf-8") == "step-000000000003"

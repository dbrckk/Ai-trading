import json
from pathlib import Path

import pytest

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


def test_published_checkpoint_rejects_model_filename_substitution(
    tmp_path: Path,
) -> None:
    store = MultiAssetCheckpointStore(tmp_path / "checkpoint")
    generation = store.commit(
        _state(1),
        {"A": {"symbol": "A"}, "B": {"symbol": "B"}},
    )
    manifest_path = store.root / generation / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    manifest["models"]["A"] = manifest["models"]["B"].copy()
    manifest_path.write_text(json.dumps(manifest, sort_keys=True), encoding="utf-8")

    with pytest.raises(ValueError, match="model filename mismatch: A"):
        store.load()


def test_unpublished_checkpoint_with_substituted_model_is_not_promoted(
    tmp_path: Path,
) -> None:
    store = MultiAssetCheckpointStore(tmp_path / "checkpoint")
    store.commit(_state(1), {"A": {"symbol": "A"}})

    # Build a complete generation through the normal writer, then restore CURRENT
    # to simulate a crash immediately before publication of the newer generation.
    store.commit(_state(2), {"A": {"symbol": "A"}, "B": {"symbol": "B"}})
    store._publish_current("step-000000000001")

    generation = "step-000000000002"
    manifest_path = store.root / generation / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["models"]["A"] = manifest["models"]["B"].copy()
    manifest_path.write_text(json.dumps(manifest, sort_keys=True), encoding="utf-8")

    loaded = store.load()

    assert loaded is not None
    loaded_state, models = loaded
    assert loaded_state.processed_bars == 1
    assert models == {"A": {"symbol": "A"}}
    assert store.current_path.read_text(encoding="utf-8") == "step-000000000001"

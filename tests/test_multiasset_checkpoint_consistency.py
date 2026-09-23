import json
from dataclasses import asdict
from pathlib import Path

import joblib
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


def _write_generation(
    store: MultiAssetCheckpointStore,
    *,
    directory_step: int,
    state_step: int,
    manifest_step: int,
    manifest_last_processed: str,
) -> None:
    directory = store.root / f"step-{directory_step:012d}"
    directory.mkdir(parents=True)
    state_path = directory / "state.json"
    state_path.write_text(
        json.dumps(asdict(_state(state_step)), sort_keys=True),
        encoding="utf-8",
    )
    model_path = directory / "A.joblib"
    joblib.dump({"learned": state_step}, model_path)
    manifest = {
        "generation": directory.name,
        "processed_bars": manifest_step,
        "last_processed": manifest_last_processed,
        "state": {"file": state_path.name, "sha256": store._sha256(state_path)},
        "models": {
            "A": {"file": model_path.name, "sha256": store._sha256(model_path)}
        },
    }
    (directory / "manifest.json").write_text(
        json.dumps(manifest, sort_keys=True), encoding="utf-8"
    )


def test_checkpoint_ignores_unpublished_generation_with_wrong_state_step(
    tmp_path: Path,
) -> None:
    store = MultiAssetCheckpointStore(tmp_path / "checkpoint")
    store.commit(_state(3), {"A": {"learned": 3}})
    _write_generation(
        store,
        directory_step=4,
        state_step=99,
        manifest_step=99,
        manifest_last_processed="bar-99",
    )

    loaded = store.load()

    assert loaded is not None
    loaded_state, models = loaded
    assert loaded_state.processed_bars == 3
    assert models == {"A": {"learned": 3}}
    assert store.current_path.read_text(encoding="utf-8") == "step-000000000003"


def test_checkpoint_fails_closed_on_published_manifest_state_mismatch(
    tmp_path: Path,
) -> None:
    store = MultiAssetCheckpointStore(tmp_path / "checkpoint")
    generation = store.commit(_state(5), {"A": {"learned": 5}})
    manifest_path = store.root / generation / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["last_processed"] = "bar-4"
    manifest_path.write_text(json.dumps(manifest, sort_keys=True), encoding="utf-8")

    with pytest.raises(ValueError, match="last processed mismatch"):
        store.load()

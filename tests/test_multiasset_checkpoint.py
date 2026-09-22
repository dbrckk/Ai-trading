import json
from dataclasses import asdict
from pathlib import Path

import joblib
import pytest

from ai_trading.multiasset_checkpoint import MultiAssetCheckpointStore
from ai_trading.multiasset_state import AssetPosition, MultiAssetState


def state(step: int) -> MultiAssetState:
    return MultiAssetState(
        cash=1000.0 - step,
        peak_equity=1100.0,
        day_start_equity=1000.0,
        positions={"A": AssetPosition(units=2.0, last_price=50.0)},
        last_processed=f"bar-{step}",
        processed_bars=step,
    )


def test_checkpoint_round_trip_state_and_models(tmp_path: Path) -> None:
    store = MultiAssetCheckpointStore(tmp_path / "checkpoint")
    generation = store.commit(state(7), {"A": {"learned": 7}})

    loaded = store.load()

    assert generation == "step-000000000007"
    assert loaded is not None
    loaded_state, models = loaded
    assert loaded_state == state(7)
    assert models == {"A": {"learned": 7}}


def test_unpublished_generation_does_not_replace_current_checkpoint(
    tmp_path: Path,
) -> None:
    store = MultiAssetCheckpointStore(tmp_path / "checkpoint")
    store.commit(state(3), {"A": {"learned": 3}})

    unpublished = store.root / "step-000000000004"
    unpublished.mkdir()
    (unpublished / "manifest.json").write_text("{}", encoding="utf-8")

    loaded = store.load()

    assert loaded is not None
    loaded_state, models = loaded
    assert loaded_state.processed_bars == 3
    assert models["A"]["learned"] == 3


def test_checkpoint_fails_closed_on_corrupted_state(tmp_path: Path) -> None:
    store = MultiAssetCheckpointStore(tmp_path / "checkpoint")
    generation = store.commit(state(9), {"A": {"learned": 9}})
    (store.root / generation / "state.json").write_text("{}", encoding="utf-8")

    with pytest.raises(ValueError, match="checksum mismatch"):
        store.load()



def test_checkpoint_refuses_to_overwrite_published_generation(tmp_path: Path) -> None:
    store = MultiAssetCheckpointStore(tmp_path / "checkpoint")
    store.commit(state(4), {"A": {"learned": 4}})

    with pytest.raises(ValueError, match="already exists"):
        store.commit(state(4), {"A": {"learned": 999}})

    loaded = store.load()
    assert loaded is not None
    loaded_state, models = loaded
    assert loaded_state.processed_bars == 4
    assert models == {"A": {"learned": 4}}


def test_checkpoint_retention_keeps_current_and_recent_generations(
    tmp_path: Path,
) -> None:
    store = MultiAssetCheckpointStore(
        tmp_path / "checkpoint",
        retain_generations=2,
    )

    for step in range(1, 5):
        store.commit(state(step), {"A": {"learned": step}})

    generations = sorted(
        path.name
        for path in store.root.glob("step-*")
        if path.is_dir()
    )

    assert generations == [
        "step-000000000003",
        "step-000000000004",
    ]
    assert store.current_path.read_text(encoding="utf-8") == "step-000000000004"


def test_checkpoint_retention_must_be_positive(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="at least 1"):
        MultiAssetCheckpointStore(
            tmp_path / "checkpoint",
            retain_generations=0,
        )



def test_checkpoint_recovers_complete_generation_not_yet_published(
    tmp_path: Path,
) -> None:
    store = MultiAssetCheckpointStore(tmp_path / "checkpoint")
    store.commit(state(1), {"A": {"learned": 1}})

    orphan = store.root / "step-000000000002"
    orphan.mkdir()
    orphan_state = state(2)
    state_path = orphan / "state.json"
    state_path.write_text(
        json.dumps(asdict(orphan_state), sort_keys=True),
        encoding="utf-8",
    )
    model_path = orphan / "A.joblib"
    joblib.dump({"learned": 2}, model_path)
    manifest = {
        "generation": "step-000000000002",
        "processed_bars": 2,
        "last_processed": orphan_state.last_processed,
        "state": {
            "file": "state.json",
            "sha256": store._sha256(state_path),
        },
        "models": {
            "A": {
                "file": "A.joblib",
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
    assert loaded_state.processed_bars == 2
    assert models == {"A": {"learned": 2}}
    assert store.current_path.read_text(encoding="utf-8") == "step-000000000002"


def test_checkpoint_ignores_invalid_newer_unpublished_generation(
    tmp_path: Path,
) -> None:
    store = MultiAssetCheckpointStore(tmp_path / "checkpoint")
    store.commit(state(3), {"A": {"learned": 3}})

    broken = store.root / "step-000000000004"
    broken.mkdir()
    (broken / "manifest.json").write_text("{}", encoding="utf-8")

    loaded = store.load()

    assert loaded is not None
    loaded_state, models = loaded
    assert loaded_state.processed_bars == 3
    assert models == {"A": {"learned": 3}}
    assert store.current_path.read_text(encoding="utf-8") == "step-000000000003"


def test_checkpoint_ignores_corrupt_compressed_unpublished_model(tmp_path: Path) -> None:
    store = MultiAssetCheckpointStore(tmp_path / "checkpoint")
    store.commit(state(3), {"A": {"learned": 3}})

    orphan = store.root / "step-000000000004"
    orphan.mkdir()
    state_path = orphan / "state.json"
    state_path.write_text(json.dumps(asdict(state(4)), sort_keys=True), encoding="utf-8")
    model_path = orphan / "A.joblib"
    model_path.write_bytes(b"\x78\x9cBADBADBAD")
    manifest = {
        "generation": orphan.name,
        "processed_bars": 4,
        "last_processed": "bar-4",
        "state": {"file": state_path.name, "sha256": store._sha256(state_path)},
        "models": {
            "A": {"file": model_path.name, "sha256": store._sha256(model_path)}
        },
    }
    (orphan / "manifest.json").write_text(
        json.dumps(manifest, sort_keys=True), encoding="utf-8"
    )

    loaded = store.load()

    assert loaded is not None
    loaded_state, models = loaded
    assert loaded_state.processed_bars == 3
    assert models == {"A": {"learned": 3}}
    assert store.current_path.read_text(encoding="utf-8") == "step-000000000003"



def test_checkpoint_rejects_pointer_path_traversal(tmp_path: Path) -> None:
    store = MultiAssetCheckpointStore(tmp_path / "checkpoint")
    store.root.mkdir(parents=True)
    store.current_path.write_text("../outside", encoding="utf-8")

    with pytest.raises(ValueError, match="invalid multiasset checkpoint generation"):
        store.load()


def test_checkpoint_model_filenames_do_not_collide_for_similar_symbols(
    tmp_path: Path,
) -> None:
    store = MultiAssetCheckpointStore(tmp_path / "checkpoint")
    store.commit(
        state(5),
        {
            "GC=F": {"learned": 1},
            "GC/F": {"learned": 2},
            "^GC_F": {"learned": 3},
        },
    )

    loaded = store.load()

    assert loaded is not None
    _, models = loaded
    assert models == {
        "GC=F": {"learned": 1},
        "GC/F": {"learned": 2},
        "^GC_F": {"learned": 3},
    }

    generation = store.current_path.read_text(encoding="utf-8")
    manifest = json.loads(
        (store.root / generation / "manifest.json").read_text(encoding="utf-8")
    )
    files = [metadata["file"] for metadata in manifest["models"].values()]
    assert len(files) == len(set(files)) == 3



def test_checkpoint_rejects_manifest_state_path_escape(tmp_path: Path) -> None:
    store = MultiAssetCheckpointStore(tmp_path / "checkpoint")
    store.commit(state(6), {"A": {"learned": 6}})

    generation = store.current_path.read_text(encoding="utf-8")
    manifest_path = store.root / generation / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["state"]["file"] = "../state.json"
    manifest_path.write_text(json.dumps(manifest, sort_keys=True), encoding="utf-8")

    with pytest.raises(ValueError, match="artifact path"):
        store.load()


def test_checkpoint_rejects_manifest_model_path_escape(tmp_path: Path) -> None:
    store = MultiAssetCheckpointStore(tmp_path / "checkpoint")
    store.commit(state(7), {"A": {"learned": 7}})

    generation = store.current_path.read_text(encoding="utf-8")
    manifest_path = store.root / generation / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["models"]["A"]["file"] = "../A.joblib"
    manifest_path.write_text(json.dumps(manifest, sort_keys=True), encoding="utf-8")

    with pytest.raises(ValueError, match="artifact path"):
        store.load()

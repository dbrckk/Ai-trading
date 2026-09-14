from pathlib import Path

from ai_trading.generations import GenerationStore


def test_generation_store_tracks_lineage_and_snapshots(tmp_path: Path) -> None:
    store = GenerationStore(
        tmp_path / "lineage.json",
        tmp_path / "generations.jsonl",
    )
    lineage = store.add_lineage("child", "parent", 1)
    assert lineage.parent == "parent"
    assert store.load_lineage()["child"].generation == 1

    first = store.snapshot(["parent"], 0.5)
    second = store.snapshot(["child"], 0.7)
    assert first.generation == 1
    assert second.generation == 2
    assert store.previous().active_experts == ("parent",)

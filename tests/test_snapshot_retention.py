from pathlib import Path

from ai_trading.state_snapshot import AtomicSnapshotStore


def test_snapshot_pruning_keeps_latest_entries(tmp_path: Path) -> None:
    artifacts = tmp_path / "artifacts"
    artifacts.mkdir()
    state = artifacts / "state.json"
    store = AtomicSnapshotStore(tmp_path / "snapshots")

    for value in range(4):
        state.write_text(f'{{"x":{value}}}', encoding="utf-8")
        store.create([state])

    removed = store.prune(keep_last=2)
    remaining = [
        p
        for p in (tmp_path / "snapshots").iterdir()
        if p.is_dir() and not p.name.startswith(".")
    ]
    assert removed == 2
    assert len(remaining) == 2

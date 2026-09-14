from pathlib import Path

from ai_trading.state_snapshot import AtomicSnapshotStore


def test_snapshot_create_validate_and_restore(tmp_path: Path) -> None:
    artifacts = tmp_path / "artifacts"
    artifacts.mkdir()
    state = artifacts / "state.json"
    state.write_text('{"x":1}', encoding="utf-8")

    store = AtomicSnapshotStore(tmp_path / "snapshots")
    snapshot = store.create([state])
    assert snapshot.exists()
    assert store.latest_valid() == snapshot

    state.write_text('{"x":999}', encoding="utf-8")
    store.restore_latest(artifacts)
    assert state.read_text(encoding="utf-8") == '{"x":1}'

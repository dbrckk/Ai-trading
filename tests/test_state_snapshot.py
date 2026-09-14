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



def test_snapshot_restores_json_and_jsonl_governance_files(tmp_path: Path) -> None:
    artifacts = tmp_path / "artifacts"
    artifacts.mkdir()
    quarantine = artifacts / "model_quarantine.json"
    champions = artifacts / "champions.jsonl"
    lifecycle = artifacts / "model_lifecycle.jsonl"

    quarantine.write_text('{"v2":{"quarantined":true}}', encoding="utf-8")
    champions.write_text('{"version":"v1"}\n', encoding="utf-8")
    lifecycle.write_text('{"event":"promotion","version":"v1"}\n', encoding="utf-8")

    store = AtomicSnapshotStore(tmp_path / "snapshots")
    snapshot = store.create([quarantine, champions, lifecycle])
    assert store.latest_valid() == snapshot

    quarantine.write_text("{}", encoding="utf-8")
    champions.write_text("", encoding="utf-8")
    lifecycle.write_text("", encoding="utf-8")

    store.restore_latest(artifacts)

    assert quarantine.read_text(encoding="utf-8") == '{"v2":{"quarantined":true}}'
    assert champions.read_text(encoding="utf-8") == '{"version":"v1"}\n'
    assert lifecycle.read_text(encoding="utf-8") == (
        '{"event":"promotion","version":"v1"}\n'
    )

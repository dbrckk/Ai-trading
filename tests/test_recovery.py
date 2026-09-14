from pathlib import Path

from ai_trading.recovery import recover_latest_consistent_state
from ai_trading.state_snapshot import AtomicSnapshotStore


def test_recovery_restores_latest_valid_snapshot(tmp_path: Path) -> None:
    artifacts = tmp_path / "artifacts"
    artifacts.mkdir()
    state = artifacts / "state.json"
    state.write_text('{"value":1}', encoding="utf-8")

    snapshots = AtomicSnapshotStore(tmp_path / "snapshots")
    snapshots.create([state])

    state.write_text('{"value":999}', encoding="utf-8")
    result = recover_latest_consistent_state(
        snapshots,
        destination_root=artifacts,
    )

    assert result.restored
    assert state.read_text(encoding="utf-8") == '{"value":1}'

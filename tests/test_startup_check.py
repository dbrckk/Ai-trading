from pathlib import Path

from ai_trading.governor_state_store import GovernorStateStore
from ai_trading.startup_check import run_startup_check
from ai_trading.state_snapshot import AtomicSnapshotStore


def test_startup_check_halts_on_invalid_state_file(tmp_path: Path) -> None:
    state = tmp_path / "state.json"
    state.write_text("not-json", encoding="utf-8")
    governor = GovernorStateStore(tmp_path / "governor.json")

    report = run_startup_check(
        audit_path=tmp_path / "audit.jsonl",
        state_files=[state],
        snapshot_store=AtomicSnapshotStore(tmp_path / "snapshots"),
        governor_store=governor,
    )

    assert not report.ready
    assert governor.load().verdict == "HALT"


def test_startup_check_allows_clean_empty_bootstrap(tmp_path: Path) -> None:
    governor = GovernorStateStore(tmp_path / "governor.json")
    report = run_startup_check(
        audit_path=tmp_path / "audit.jsonl",
        state_files=[],
        snapshot_store=AtomicSnapshotStore(tmp_path / "snapshots"),
        governor_store=governor,
    )
    assert report.ready

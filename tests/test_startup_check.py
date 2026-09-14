from pathlib import Path

from ai_trading.champions import ChampionRegistry
from ai_trading.governor_state_store import GovernorStateStore
from ai_trading.lifecycle_log import LifecycleEventLog
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



def test_startup_check_halts_on_invalid_governance_jsonl(tmp_path: Path) -> None:
    governor = GovernorStateStore(tmp_path / "governor.json")
    lifecycle = tmp_path / "model_lifecycle.jsonl"
    lifecycle.write_text("not-json\n", encoding="utf-8")

    report = run_startup_check(
        audit_path=tmp_path / "audit.jsonl",
        state_files=[],
        jsonl_files=[lifecycle],
        snapshot_store=AtomicSnapshotStore(tmp_path / "snapshots"),
        governor_store=governor,
    )

    assert not report.ready
    assert not report.jsonl_files_valid
    assert governor.load().verdict == "HALT"


def test_startup_check_halts_on_corrupted_active_artifact(tmp_path: Path) -> None:
    governor = GovernorStateStore(tmp_path / "governor.json")
    registry = ChampionRegistry(tmp_path / "champions.jsonl")
    lifecycle = LifecycleEventLog(tmp_path / "model_lifecycle.jsonl")
    artifact = tmp_path / "model.joblib"
    artifact.write_bytes(b"valid-model")

    registry.promote(
        version="v2",
        model_name="ensemble",
        score=1.2,
        metrics={"sharpe": 1.2},
        config={},
    )
    lifecycle.append(
        event="promotion",
        version="v2",
        model_name="ensemble",
        artifact_path=artifact,
    )
    artifact.write_bytes(b"corrupted-model")

    report = run_startup_check(
        audit_path=tmp_path / "audit.jsonl",
        state_files=[],
        jsonl_files=[registry.path, lifecycle.path],
        snapshot_store=AtomicSnapshotStore(tmp_path / "snapshots"),
        governor_store=governor,
        champion_registry=registry,
        lifecycle_log=lifecycle,
    )

    assert not report.ready
    assert not report.active_artifact_valid
    assert "active champion artifact integrity check failed" in report.reasons
    assert governor.load().verdict == "HALT"

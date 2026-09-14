from pathlib import Path

from ai_trading.audit import AuditLog
from ai_trading.recovery import recover_latest_consistent_state
from ai_trading.session_integrity import compute_session_fingerprint
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



def test_recovery_skips_newer_logically_inconsistent_snapshot(
    tmp_path: Path,
) -> None:
    artifacts = tmp_path / "artifacts"
    artifacts.mkdir()
    state = artifacts / "state.json"
    audit = AuditLog(artifacts / "audit.jsonl")
    snapshots = AtomicSnapshotStore(tmp_path / "snapshots")

    state.write_text('{"value":1}', encoding="utf-8")
    first = snapshots.create([state])
    first_fp = compute_session_fingerprint([state], audit.path)
    audit.append(
        "session_checkpoint",
        {
            "snapshot": str(first),
            "fingerprint": first_fp.fingerprint,
            "state_hashes": first_fp.state_hashes,
            "audit_tail_hash": first_fp.audit_tail_hash,
        },
    )

    state.write_text('{"value":2}', encoding="utf-8")
    second = snapshots.create([state])
    second_fp = compute_session_fingerprint([state], audit.path)
    bad_hashes = dict(second_fp.state_hashes)
    bad_hashes["state.json"] = "intentionally-invalid"
    audit.append(
        "session_checkpoint",
        {
            "snapshot": str(second),
            "fingerprint": second_fp.fingerprint,
            "state_hashes": bad_hashes,
            "audit_tail_hash": second_fp.audit_tail_hash,
        },
    )

    state.write_text('{"value":999}', encoding="utf-8")
    result = recover_latest_consistent_state(
        snapshots,
        destination_root=artifacts,
        audit_path=audit.path,
        state_files=[state],
    )

    assert result.restored
    assert result.verified
    assert result.snapshot == str(first)
    assert result.candidates_tested == 2
    assert result.fallback_depth == 1
    assert state.read_text(encoding="utf-8") == '{"value":1}'



def test_failed_multi_snapshot_recovery_restores_pre_attempt_state(
    tmp_path: Path,
) -> None:
    artifacts = tmp_path / "artifacts"
    artifacts.mkdir()
    state = artifacts / "state.json"
    audit = AuditLog(artifacts / "audit.jsonl")
    snapshots = AtomicSnapshotStore(tmp_path / "snapshots")

    state.write_text('{"value":1}', encoding="utf-8")
    snapshot = snapshots.create([state])
    fingerprint = compute_session_fingerprint([state], audit.path)
    bad_hashes = dict(fingerprint.state_hashes)
    bad_hashes["state.json"] = "not-a-real-hash"
    audit.append(
        "session_checkpoint",
        {
            "snapshot": str(snapshot),
            "fingerprint": fingerprint.fingerprint,
            "state_hashes": bad_hashes,
            "audit_tail_hash": fingerprint.audit_tail_hash,
        },
    )

    state.write_text('{"value":999}', encoding="utf-8")
    result = recover_latest_consistent_state(
        snapshots,
        destination_root=artifacts,
        audit_path=audit.path,
        state_files=[state],
    )

    assert not result.restored
    assert not result.verified
    assert result.candidates_tested == 1
    assert result.fallback_depth == 0
    assert state.read_text(encoding="utf-8") == '{"value":999}'

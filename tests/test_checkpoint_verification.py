from pathlib import Path

from ai_trading.audit import AuditLog
from ai_trading.checkpoint_verification import verify_checkpoint_state
from ai_trading.session_integrity import compute_session_fingerprint


def test_checkpoint_verification_detects_matching_state(tmp_path: Path) -> None:
    state = tmp_path / "state.json"
    audit_path = tmp_path / "audit.jsonl"
    snapshot = tmp_path / "snapshots" / "one"
    snapshot.mkdir(parents=True)

    state.write_text('{"x":1}', encoding="utf-8")
    audit = AuditLog(audit_path)
    fingerprint = compute_session_fingerprint([state], audit_path)
    audit.append(
        "session_checkpoint",
        {
            "snapshot": str(snapshot),
            "fingerprint": fingerprint.fingerprint,
            "state_hashes": fingerprint.state_hashes,
            "audit_tail_hash": fingerprint.audit_tail_hash,
        },
    )

    result = verify_checkpoint_state(
        audit_path,
        snapshot,
        [state],
    )
    assert result.valid
    assert result.matched_checkpoint

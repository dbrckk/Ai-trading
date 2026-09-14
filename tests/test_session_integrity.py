from pathlib import Path

from ai_trading.audit import AuditLog
from ai_trading.session_integrity import compute_session_fingerprint


def test_session_fingerprint_changes_with_state(tmp_path: Path) -> None:
    state = tmp_path / "state.json"
    audit_path = tmp_path / "audit.jsonl"
    state.write_text('{"x":1}', encoding="utf-8")
    AuditLog(audit_path).append("start", {"ok": True})

    first = compute_session_fingerprint([state], audit_path)
    state.write_text('{"x":2}', encoding="utf-8")
    second = compute_session_fingerprint([state], audit_path)

    assert first.fingerprint != second.fingerprint
    assert first.audit_tail_hash == second.audit_tail_hash

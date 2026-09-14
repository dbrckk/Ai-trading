from pathlib import Path

from ai_trading.audit import AuditLog
from ai_trading.audit_chain import verify_audit_chain


def test_legacy_prefix_can_transition_to_chained_audit(tmp_path: Path) -> None:
    path = tmp_path / "audit.jsonl"
    path.write_text(
        '{"event":"legacy","payload":{"x":1},"timestamp_utc":"old"}\n',
        encoding="utf-8",
    )
    AuditLog(path).append("new", {"x": 2})

    report = verify_audit_chain(path)
    assert report.valid
    assert report.legacy_lines == 1
    assert report.lines == 2

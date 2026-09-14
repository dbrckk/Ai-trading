from pathlib import Path

from ai_trading.audit import AuditLog
from ai_trading.audit_chain import verify_audit_chain


def test_audit_chain_detects_tampering(tmp_path: Path) -> None:
    path = tmp_path / "audit.jsonl"
    audit = AuditLog(path)
    audit.append("one", {"x": 1})
    audit.append("two", {"x": 2})

    valid = verify_audit_chain(path)
    assert valid.valid
    assert valid.lines == 2

    content = path.read_text(encoding="utf-8").replace('"x": 2', '"x": 999')
    path.write_text(content, encoding="utf-8")

    broken = verify_audit_chain(path)
    assert not broken.valid
    assert broken.invalid_line == 2

import json
from pathlib import Path

from ai_trading.audit import AuditLog


def test_audit_log_is_append_only(tmp_path: Path) -> None:
    path = tmp_path / "audit.jsonl"
    log = AuditLog(path)
    log.append("one", {"value": 1})
    log.append("two", {"value": 2})

    lines = path.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 2
    assert json.loads(lines[0])["event"] == "one"
    assert json.loads(lines[1])["event"] == "two"

import json
from pathlib import Path

from ai_trading.audit import AuditLog, build_audit_record


def test_audit_log_is_append_only(tmp_path: Path) -> None:
    path = tmp_path / "audit.jsonl"
    log = AuditLog(path)
    log.append("one", {"value": 1})
    log.append("two", {"value": 2})

    lines = path.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 2
    assert json.loads(lines[0])["event"] == "one"
    assert json.loads(lines[1])["event"] == "two"


def test_build_audit_record_uses_supplied_previous_hash() -> None:
    record = build_audit_record(
        "runtime_step",
        {"processed_bars": 1},
        "GENESIS",
        timestamp_utc="2026-09-15T00:00:00+00:00",
    )

    assert record["timestamp_utc"] == "2026-09-15T00:00:00+00:00"
    assert record["prev_hash"] == "GENESIS"
    assert len(record["hash"]) == 64

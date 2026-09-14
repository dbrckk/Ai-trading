from pathlib import Path

from ai_trading.audit_integrity import verify_jsonl_audit


def test_audit_integrity_accepts_valid_jsonl(tmp_path: Path) -> None:
    path = tmp_path / "audit.jsonl"
    path.write_text('{"a":1}\n{"b":2}\n', encoding="utf-8")
    report = verify_jsonl_audit(path)
    assert report.valid
    assert report.lines == 2


def test_audit_integrity_rejects_invalid_jsonl(tmp_path: Path) -> None:
    path = tmp_path / "audit.jsonl"
    path.write_text('{"a":1}\nnot-json\n', encoding="utf-8")
    report = verify_jsonl_audit(path)
    assert not report.valid
    assert report.invalid_line == 2

from pathlib import Path

from ai_trading.state_hash import canonical_state_hash, file_state_hash


def test_state_hash_is_order_independent() -> None:
    left = {"a": 1, "b": {"x": 2, "y": 3}}
    right = {"b": {"y": 3, "x": 2}, "a": 1}
    assert canonical_state_hash(left) == canonical_state_hash(right)


def test_file_state_hash_detects_change(tmp_path: Path) -> None:
    path = tmp_path / "state.json"
    path.write_text('{"a":1}', encoding="utf-8")
    first = file_state_hash(path)
    path.write_text('{"a":2}', encoding="utf-8")
    second = file_state_hash(path)
    assert first != second

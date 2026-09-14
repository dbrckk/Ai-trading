from pathlib import Path

from ai_trading.readiness_revocation import ReadinessRevocationStore


def test_readiness_revocation_round_trip(tmp_path: Path) -> None:
    store = ReadinessRevocationStore(tmp_path / "revocations.jsonl")

    record = store.revoke("abc123", reason="superseded")

    assert store.is_revoked("abc123")
    assert store.list() == [record]


def test_readiness_revocation_is_idempotent(tmp_path: Path) -> None:
    store = ReadinessRevocationStore(tmp_path / "revocations.jsonl")

    first = store.revoke("abc123", reason="superseded")
    second = store.revoke("abc123", reason="duplicate")

    assert second == first
    assert len(store.list()) == 1

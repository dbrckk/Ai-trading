from pathlib import Path

from ai_trading.model_quarantine import ModelQuarantineStore, QuarantinePolicy


def test_quarantine_backoff_grows_after_failures(tmp_path: Path) -> None:
    store = ModelQuarantineStore(tmp_path / "quarantine.json")
    policy = QuarantinePolicy(
        failures_before_quarantine=3,
        base_backoff_bars=10,
        max_backoff_bars=100,
    )

    first = store.record_failure(
        "v2",
        processed_bar=100,
        reason="first",
        policy=policy,
    )
    second = store.record_failure(
        "v2",
        processed_bar=110,
        reason="second",
        policy=policy,
    )

    assert first.next_eligible_bar == 110
    assert second.next_eligible_bar == 130
    assert not second.quarantined


def test_quarantine_blocks_version_after_threshold(tmp_path: Path) -> None:
    store = ModelQuarantineStore(tmp_path / "quarantine.json")
    policy = QuarantinePolicy(
        failures_before_quarantine=2,
        base_backoff_bars=5,
        max_backoff_bars=100,
    )

    store.record_failure("v2", processed_bar=10, reason="one", policy=policy)
    record = store.record_failure(
        "v2",
        processed_bar=20,
        reason="two",
        policy=policy,
    )

    assert record.quarantined
    assert not store.eligible("v2", processed_bar=1000)

    released = store.release("v2")
    assert not released.quarantined
    assert store.eligible("v2", processed_bar=1000)


def test_success_resets_failure_history(tmp_path: Path) -> None:
    store = ModelQuarantineStore(tmp_path / "quarantine.json")
    store.record_failure("v2", processed_bar=10, reason="bad")
    record = store.record_success("v2")

    assert record.failures == 0
    assert not record.quarantined
    assert store.eligible("v2", processed_bar=10)

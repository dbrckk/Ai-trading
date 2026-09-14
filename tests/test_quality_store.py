from pathlib import Path

from ai_trading.quality_store import QualityStore


def test_quality_store_is_bounded_and_persistent(tmp_path: Path) -> None:
    store = QualityStore(tmp_path / "quality.json")
    for i in range(20):
        store.append(
            "A:river",
            prediction=1,
            confidence=0.7,
            label=1 if i % 2 == 0 else -1,
            maxlen=5,
        )
    record = store.load()["A:river"]
    assert len(record.predictions) == 5
    assert len(record.confidences) == 5
    assert len(record.labels) == 5

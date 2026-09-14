from pathlib import Path

from ai_trading.drift_retrain_store import DriftRetrainStore


def test_drift_retrain_store_enforces_cooldown(tmp_path: Path) -> None:
    store = DriftRetrainStore(tmp_path / "drift.json")
    assert store.should_retrain("GC=F", processed_bar=100, cooldown_bars=20)

    store.mark(
        "GC=F",
        processed_bar=100,
        max_psi=0.4,
        correlation_shift=0.2,
    )

    assert not store.should_retrain(
        "GC=F",
        processed_bar=110,
        cooldown_bars=20,
    )
    assert store.should_retrain(
        "GC=F",
        processed_bar=120,
        cooldown_bars=20,
    )

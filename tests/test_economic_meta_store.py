from pathlib import Path

from ai_trading.economic_meta_store import EconomicMetaStore


def test_economic_meta_store_persists_updates(tmp_path: Path) -> None:
    store = EconomicMetaStore(tmp_path / "economic.json")
    updated = store.update(
        "GC=F|river|bull",
        pnl=100.0,
        turnover=1_000.0,
        costs=5.0,
        drawdown=0.01,
        equity=100_000.0,
    )
    loaded = store.load()["GC=F|river|bull"]
    assert loaded == updated
    assert loaded.observations == 1

from pathlib import Path

from ai_trading.maintenance import MaintenanceState, MaintenanceStore


def test_maintenance_round_trip(tmp_path: Path) -> None:
    store = MaintenanceStore(tmp_path / "maintenance.json")
    state = MaintenanceState(enabled=True, reason="upgrade")
    store.save(state)
    assert store.load() == state

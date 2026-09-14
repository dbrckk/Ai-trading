from pathlib import Path

import pytest

from ai_trading.supervisor_lease import SupervisorLeaseStore


def test_supervisor_lease_is_exclusive_for_current_pid(tmp_path: Path) -> None:
    store = SupervisorLeaseStore(tmp_path / "lease.json")
    lease = store.acquire("one")
    assert lease.owner_pid > 0

    with pytest.raises(RuntimeError, match="already owned"):
        store.acquire("two")

    store.release("one")
    assert store.load() is None

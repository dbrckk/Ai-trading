from pathlib import Path

import pytest

from ai_trading.runtime_lock import RuntimeLock


def test_runtime_lock_is_exclusive(tmp_path: Path) -> None:
    path = tmp_path / "runtime.lock"
    with RuntimeLock(path), pytest.raises(RuntimeError), RuntimeLock(path):
        pass
    assert not path.exists()

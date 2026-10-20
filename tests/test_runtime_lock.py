from pathlib import Path

import pytest

from ai_trading.runtime import PaperAutonomousRuntime
from ai_trading.runtime_lock import RuntimeLock


def test_runtime_lock_is_exclusive(tmp_path: Path, monkeypatch) -> None:
    path = tmp_path / "runtime.lock"
    with RuntimeLock(path), pytest.raises(RuntimeError), RuntimeLock(path):
        pass
    assert not path.exists()

    monkeypatch.chdir(tmp_path)
    shared_backend = object()
    gold = PaperAutonomousRuntime(
        symbol="GC=F", runtime_key="paper:GC=F:5m:online-river:v1",
        persistence=shared_backend,
    )
    same_gold = PaperAutonomousRuntime(
        symbol="GC=F", runtime_key="paper:GC=F:5m:online-river:v1",
        persistence=shared_backend,
    )
    btc = PaperAutonomousRuntime(
        symbol="BTC-USD", runtime_key="paper:BTC-USD:5m:online-river:v1",
        persistence=shared_backend,
    )
    assert gold.lock_path == same_gold.lock_path
    assert gold.lock_path != btc.lock_path
    with RuntimeLock(gold.lock_path), RuntimeLock(btc.lock_path):
        with pytest.raises(RuntimeError, match="runtime is already active"):
            with RuntimeLock(same_gold.lock_path):
                pass
    assert not gold.lock_path.exists()
    assert not btc.lock_path.exists()
    assert PaperAutonomousRuntime().lock_path == Path("artifacts/runtime.lock")
    custom = tmp_path / "custom.lock"
    assert PaperAutonomousRuntime(lock_path=custom).lock_path == custom

from pathlib import Path

import numpy as np
import pandas as pd

from ai_trading.multiasset_scheduler import (
    MultiAssetPaperScheduler,
    MultiAssetSchedulerConfig,
)
from ai_trading.runtime_factory import isolated_multiasset_runtime
from ai_trading.state_snapshot import AtomicSnapshotStore
from ai_trading.watchdog import HeartbeatStore


def market(seed: int, n: int = 180) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    index = pd.date_range("2025-01-01", periods=n, freq="D")
    returns = rng.normal(0.0003, 0.01, n)
    close = 100.0 * np.cumprod(1.0 + returns)
    open_ = close * (1.0 + rng.normal(0.0, 0.001, n))
    return pd.DataFrame(
        {
            "Open": open_,
            "High": np.maximum(open_, close) * 1.005,
            "Low": np.minimum(open_, close) * 0.995,
            "Close": close,
            "Volume": 1000.0 + np.arange(n),
        },
        index=index,
    )


def test_end_to_end_paper_smoke(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    runtime = isolated_multiasset_runtime(workspace)
    markets = {
        "GC=F": market(1),
        "SI=F": market(2),
        "CL=F": market(3),
    }
    scheduler = MultiAssetPaperScheduler(
        runtime=runtime,
        data_loader=lambda: markets,
        config=MultiAssetSchedulerConfig(
            poll_seconds=0.0,
            max_iterations=1,
            max_consecutive_errors=1,
            snapshot_every_iterations=1,
            verify_audit_every_iterations=1,
        ),
        heartbeat_store=HeartbeatStore(workspace / "heartbeat.json"),
        snapshot_store=AtomicSnapshotStore(workspace / "snapshots"),
    )

    results = scheduler.run()

    assert len(results) == 1
    result = results[0]
    assert result.processed
    assert result.equity > 0
    assert runtime.state_store.path.exists()
    assert runtime.audit.path.exists()
    assert runtime.resilience_state_store.path.exists()
    assert scheduler.snapshot_store.latest_valid() is not None

    heartbeat = (workspace / "heartbeat.json").read_text(encoding="utf-8")
    assert '"status": "stopped"' in heartbeat

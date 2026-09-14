from pathlib import Path

import numpy as np
import pandas as pd

from ai_trading.audit import AuditLog
from ai_trading.config import RiskConfig
from ai_trading.runtime import PaperAutonomousRuntime
from ai_trading.runtime_state import RuntimeStateStore


def sample_market(n: int = 100) -> pd.DataFrame:
    idx = pd.date_range("2025-01-01", periods=n, freq="D")
    t = np.arange(n, dtype=float)
    close = 100.0 + 0.1 * t + 2.0 * np.sin(t / 5.0)
    open_ = close * (1.0 + 0.001 * np.sin(t / 3.0))
    return pd.DataFrame(
        {
            "Open": open_,
            "High": np.maximum(open_, close) * 1.005,
            "Low": np.minimum(open_, close) * 0.995,
            "Close": close,
            "Volume": 1000.0 + t,
        },
        index=idx,
    )


def test_runtime_step_is_persistent_and_idempotent(tmp_path: Path) -> None:
    runtime = PaperAutonomousRuntime(
        risk_config=RiskConfig(min_confidence=0.0),
        state_store=RuntimeStateStore(tmp_path / "state.json"),
        audit_log=AuditLog(tmp_path / "audit.jsonl"),
        online_model_path=tmp_path / "online.joblib",
        lock_path=tmp_path / "runtime.lock",
        learning_cycle_every_bars=2,
    )
    df = sample_market()

    first = runtime.step(df)
    second = runtime.step(df)

    assert first.processed
    assert first.processed_bars == 1
    assert not second.processed
    assert second.reason == "bar already processed"

    next_df = sample_market(101)
    third = runtime.step(next_df)
    assert third.processed
    assert third.processed_bars == 2
    assert third.retrain_due

from pathlib import Path

import numpy as np
import pandas as pd

from ai_trading.audit import AuditLog
from ai_trading.config import RiskConfig
from ai_trading.multiasset_runtime import MultiAssetPaperRuntime
from ai_trading.multiasset_state import MultiAssetStateStore
from ai_trading.portfolio import AllocationConfig
from ai_trading.portfolio_risk import PortfolioRiskConfig


def market(seed: int, n: int = 120) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    idx = pd.date_range("2025-01-01", periods=n, freq="D")
    rets = rng.normal(0.0003, 0.01, n)
    close = 100.0 * np.cumprod(1.0 + rets)
    open_ = close * (1.0 + rng.normal(0.0, 0.001, n))
    return pd.DataFrame(
        {
            "Open": open_,
            "High": np.maximum(open_, close) * 1.005,
            "Low": np.minimum(open_, close) * 0.995,
            "Close": close,
            "Volume": 1000.0 + np.arange(n),
        },
        index=idx,
    )


def test_multiasset_runtime_is_persistent_and_idempotent(tmp_path: Path) -> None:
    runtime = MultiAssetPaperRuntime(
        risk_config=RiskConfig(),
        allocation_config=AllocationConfig(max_asset_weight=0.6),
        portfolio_risk_config=PortfolioRiskConfig(
            max_gross_exposure=1.0,
            max_net_exposure=1.0,
            max_asset_exposure=0.6,
            max_pair_correlation=0.99,
        ),
        state_store=MultiAssetStateStore(tmp_path / "state.json"),
        audit_log=AuditLog(tmp_path / "audit.jsonl"),
        lock_path=str(tmp_path / "lock"),
    )
    markets = {"A": market(1), "B": market(2)}

    first = runtime.step(markets)
    second = runtime.step(markets)

    assert first.processed
    assert first.risk_approved
    assert first.equity > 0
    assert sum(abs(v) for v in first.weights.values()) <= 1.0 + 1e-9
    assert not second.processed
    assert "bar already processed" in second.risk_reasons

from pathlib import Path

import numpy as np
import pandas as pd

from ai_trading.config import RiskConfig
from ai_trading.file_persistence import FilePaperPersistence
from ai_trading.paper_cycle import PaperCycleRunner
from ai_trading.runtime import PaperAutonomousRuntime
from ai_trading.runtime_state import RuntimeState


def sample_market(n: int = 110) -> pd.DataFrame:
    idx = pd.date_range("2025-01-01", periods=n, freq="5min")
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


def test_materialized_empty_runtime_is_treated_as_fresh(tmp_path: Path) -> None:
    backend = FilePaperPersistence(tmp_path)
    backend.state_store.save(
        RuntimeState(
            cash=100_000.0,
            units=0.0,
            last_price=0.0,
            peak_equity=100_000.0,
            day_start_equity=100_000.0,
            last_processed=None,
            processed_bars=0,
            last_learning_cycle_bar=0,
        )
    )
    market = sample_market()

    def runtime_factory(**kwargs) -> PaperAutonomousRuntime:
        return PaperAutonomousRuntime(
            risk_config=RiskConfig(min_confidence=0.0),
            lock_path=tmp_path / "runtime.lock",
            **kwargs,
        )

    runtime = runtime_factory(
        symbol="GC=F",
        persistence=backend,
        runtime_key="paper:GC=F:5m:online-river:v1",
    )
    eligible = runtime._eligible_execution_indices(market)
    runner = PaperCycleRunner(
        persistence=backend,
        data_loader=lambda symbol, period, interval: market,
        runtime_factory=runtime_factory,
    )

    result = runner.run_once(
        symbol="GC=F",
        period="5d",
        interval="5m",
        max_catchup_bars=12,
    )

    assert result.processed == 1
    assert result.remaining_backlog is False
    assert result.last_processed == str(eligible[-1])
    assert result.processed_bars == 1

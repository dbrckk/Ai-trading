import os
from pathlib import Path
from uuid import uuid4

import numpy as np
import pandas as pd
import pytest

from ai_trading.config import RiskConfig
from ai_trading.paper_cycle import PaperCycleRunner
from ai_trading.persistence import build_runtime_key
from ai_trading.postgres_persistence import PostgresPaperPersistence
from ai_trading.runtime import PaperAutonomousRuntime


def sample_market(n: int) -> pd.DataFrame:
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


def runtime_factory(lock_path: Path):
    def build(**kwargs) -> PaperAutonomousRuntime:
        return PaperAutonomousRuntime(
            risk_config=RiskConfig(min_confidence=0.0),
            lock_path=lock_path,
            **kwargs,
        )

    return build


@pytest.mark.skipif(
    not os.environ.get("TEST_DATABASE_URL"),
    reason="TEST_DATABASE_URL is required for PostgreSQL integration",
)
def test_paper_cycle_survives_postgres_object_reconstruction(tmp_path: Path) -> None:
    database_url = os.environ["TEST_DATABASE_URL"]
    symbol = f"PAPER-CYCLE-{uuid4().hex[:8]}"
    interval = "5m"
    runtime_key = build_runtime_key(symbol, interval)
    first_market = sample_market(105)
    second_market = sample_market(110)

    first_persistence = PostgresPaperPersistence(database_url)
    first_persistence.initialize_schema()
    first_runner = PaperCycleRunner(
        persistence=first_persistence,
        data_loader=lambda _symbol, _period, _interval: first_market,
        runtime_factory=runtime_factory(tmp_path / "first.lock"),
    )

    first_result = first_runner.run_once(
        symbol=symbol,
        period="5d",
        interval=interval,
        max_catchup_bars=12,
    )
    first_snapshot = first_persistence.load_runtime(runtime_key, 100_000.0)

    second_persistence = PostgresPaperPersistence(database_url)
    second_persistence.initialize_schema()
    second_runner = PaperCycleRunner(
        persistence=second_persistence,
        data_loader=lambda _symbol, _period, _interval: second_market,
        runtime_factory=runtime_factory(tmp_path / "second.lock"),
    )
    eligibility_runtime = runtime_factory(tmp_path / "eligibility.lock")(
        symbol=symbol,
        persistence=second_persistence,
        runtime_key=runtime_key,
    )
    expected_latest = eligibility_runtime._eligible_execution_indices(second_market)[-1]

    second_result = second_runner.run_once(
        symbol=symbol,
        period="5d",
        interval=interval,
        max_catchup_bars=12,
    )
    final = second_persistence.load_runtime(runtime_key, 100_000.0)

    assert first_result.processed == 1
    assert first_snapshot.state.processed_bars == 1
    assert first_snapshot.model is not None
    assert second_result.processed >= 1
    assert final.revision == final.state.processed_bars
    assert final.state.processed_bars > first_snapshot.state.processed_bars
    assert final.state.last_processed == str(expected_latest)
    assert final.model is not None

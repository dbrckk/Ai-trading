import numpy as np
import pandas as pd

from ai_trading.expert_pool import ExpertPoolStore, ExpertRecord
from ai_trading.generations import GenerationStore
from ai_trading.multiasset_evolution import run_multiasset_evolution_cycle


def market(seed: int, n: int = 360) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    idx = pd.date_range("2023-01-01", periods=n, freq="D")
    t = np.arange(n, dtype=float)
    noise = rng.normal(0.0, 0.3, n)
    close = 100 + 0.04 * t + 3.0 * np.sin(t / (7.0 + seed)) + noise
    open_ = close * (1.0 + 0.001 * np.sin(t / (4.0 + seed)))
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


def test_multiasset_evolution_runs_with_global_generation_store(tmp_path) -> None:
    pool = ExpertPoolStore(tmp_path / "pool.json")
    generations = GenerationStore(
        tmp_path / "lineage.json",
        tmp_path / "generations.jsonl",
    )
    pool.save(
        {
            "A:trend:h3:t0.001": ExpertRecord(
                "A:trend:h3:t0.001",
                "trend",
                "active",
                score=0.8,
                validation_score=0.8,
                observations=100,
            ),
            "B:trend:h3:t0.001": ExpertRecord(
                "B:trend:h3:t0.001",
                "trend",
                "active",
                score=0.8,
                validation_score=0.8,
                observations=100,
            ),
        }
    )

    result = run_multiasset_evolution_cycle(
        {"A": market(1), "B": market(2)},
        pool=pool,
        generations=generations,
        parent_limit=1,
    )
    assert result.generation >= 1
    assert result.symbols == ("A", "B")
    assert isinstance(result.accepted, bool)
    assert isinstance(result.rolled_back, bool)

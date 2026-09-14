from types import SimpleNamespace

import pandas as pd

import ai_trading.expert_factory as factory_module
from ai_trading.expert_factory import FactoryConfig, run_expert_factory
from ai_trading.expert_pool import ExpertPoolStore


def test_factory_propagates_candidate_horizon(tmp_path, monkeypatch) -> None:
    seen: list[int] = []

    def fake_validate(
        df: pd.DataFrame,
        *,
        kind: str,
        train_fraction: float = 0.70,
        return_threshold: float = 0.001,
        horizon_bars: int = 1,
    ):
        del df, kind, train_fraction, return_threshold
        seen.append(horizon_bars)
        return SimpleNamespace(
            validation_score=0.80,
            observations=100,
        )

    monkeypatch.setattr(factory_module, "validate_specialist", fake_validate)
    monkeypatch.setattr(factory_module, "promotions_allowed", lambda: True)

    run_expert_factory(
        pd.DataFrame({"Close": [1.0]}),
        symbol="GC=F",
        store=ExpertPoolStore(tmp_path / "pool.json"),
        config=FactoryConfig(
            horizons=(3,),
            return_thresholds=(0.001,),
            kinds=("trend",),
            max_candidates=1,
            max_promotions_per_run=1,
        ),
    )

    assert seen == [3]

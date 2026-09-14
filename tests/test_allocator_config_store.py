from pathlib import Path

from ai_trading.allocator_config_store import AllocatorConfigStore
from ai_trading.global_allocator import GlobalAllocatorConfig


def test_allocator_config_store_round_trip(tmp_path: Path) -> None:
    store = AllocatorConfigStore(tmp_path / "allocator.json")
    config = GlobalAllocatorConfig(
        cvar_alpha=0.97,
        max_cvar=0.04,
        max_asset_weight=0.35,
        max_expert_weight=0.20,
        max_turnover=0.75,
        target_gross_exposure=0.80,
        cost_penalty=1.2,
        turnover_penalty=0.15,
    )
    store.save(config)
    assert store.load() == config

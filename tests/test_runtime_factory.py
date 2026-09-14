from pathlib import Path

from ai_trading.runtime_factory import isolated_multiasset_runtime


def test_isolated_runtime_routes_artifacts_to_workspace(tmp_path: Path) -> None:
    runtime = isolated_multiasset_runtime(tmp_path / "soak")
    root = tmp_path / "soak"

    assert runtime.state_store.path == root / "multiasset_state.json"
    assert runtime.audit.path == root / "multiasset_audit.jsonl"
    assert runtime.quality_store.path == root / "model_quality.json"
    assert runtime.meta_store.path == root / "meta_router.json"
    assert runtime.economic_meta_store.path == root / "economic_meta.json"
    assert runtime.expert_pool_store.path == root / "expert_pool.json"
    assert runtime.allocation_state_store.path == root / "global_allocation.json"
    assert runtime.crisis_state_store.path == root / "crisis_state.json"
    assert runtime.governor_state_store.path == root / "risk_governor_state.json"
    assert runtime.champion_registry.path == root / "champions.jsonl"
    assert runtime.champion_probation_store.path == root / "champion_probation.json"
    assert runtime.model_quarantine_store.path == root / "model_quarantine.json"
    assert runtime.lifecycle_log.path == root / "model_lifecycle.jsonl"
    assert runtime.resilience_state_store.path == root / "resilience_state.json"
    assert runtime.readiness_history_store.path == root / "readiness_history.jsonl"

from pathlib import Path

from ai_trading.champions import ChampionRegistry
from ai_trading.drift import DriftReport
from ai_trading.guardrails import evaluate_health, rollback_if_needed
from ai_trading.performance import PerformanceMetrics
from ai_trading.persistence import ModelStore


def metrics() -> PerformanceMetrics:
    return PerformanceMetrics(
        total_return=0.1,
        annualized_return=0.1,
        annualized_volatility=0.1,
        sharpe=1.0,
        sortino=1.1,
        max_drawdown=0.08,
        calmar=1.25,
    )


def test_rollback_restores_previous_model_artifact(tmp_path: Path) -> None:
    registry = ChampionRegistry(tmp_path / "champions.jsonl")
    store = ModelStore(tmp_path / "models")

    for version, model_id in [("v1", 1), ("v2", 2)]:
        store.save(version, {"id": model_id})
        registry.promote(
            version=version,
            model_name="ensemble",
            score=float(model_id),
            metrics=metrics().as_dict(),
            config={},
        )
    store.activate("v2")

    drift = DriftReport(2.0, 0.0, True, ("feature distribution drift",))
    decision = evaluate_health(metrics(), drift)
    restored = rollback_if_needed(registry, decision, store)

    assert restored is not None
    assert restored.version == "v1"
    assert store.active_name() == "v1"
    assert store.load_active_model() == {"id": 1}

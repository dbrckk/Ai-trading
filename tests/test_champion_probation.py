from pathlib import Path

from ai_trading.champion_probation import (
    ChampionProbationManager,
    ChampionProbationStore,
    ProbationPolicy,
)
from ai_trading.champions import ChampionRegistry
from ai_trading.model_quarantine import ModelQuarantineStore


BASELINE = {
    "sharpe": 1.0,
    "sortino": 1.2,
    "max_drawdown": 0.10,
    "calmar": 1.1,
}


def seeded_registry(tmp_path: Path) -> tuple[ChampionRegistry, object]:
    registry = ChampionRegistry(tmp_path / "champions.jsonl")
    registry.promote(
        version="v1",
        model_name="baseline",
        score=1.0,
        metrics=BASELINE,
        config={},
    )
    champion = registry.promote(
        version="v2",
        model_name="challenger",
        score=1.1,
        metrics=BASELINE,
        config={},
    )
    return registry, champion


def test_probation_passes_after_enough_healthy_observations(tmp_path: Path) -> None:
    registry, champion = seeded_registry(tmp_path)
    store = ChampionProbationStore(tmp_path / "probation.json")
    manager = ChampionProbationManager(
        registry,
        store=store,
        policy=ProbationPolicy(min_observations=2),
    )
    manager.start(champion)

    first = manager.observe(BASELINE)
    second = manager.observe(BASELINE)

    assert first.action == "continue"
    assert second.action == "pass"
    assert store.load() is not None
    assert store.load().status == "passed"
    assert registry.active() == champion


def test_probation_rolls_back_on_hard_drawdown_breach(tmp_path: Path) -> None:
    registry, champion = seeded_registry(tmp_path)
    manager = ChampionProbationManager(
        registry,
        store=ChampionProbationStore(tmp_path / "probation.json"),
    )
    manager.start(champion)

    result = manager.observe(
        {
            "sharpe": 1.0,
            "sortino": 1.2,
            "max_drawdown": 0.18,
            "calmar": 1.1,
        }
    )

    assert result.action == "rollback"
    assert result.state.status == "rolled_back"
    assert result.state.failure_count == 1
    assert registry.active() is not None
    assert registry.active().version == "v1"


def test_probation_rolls_back_after_persistent_quality_degradation(
    tmp_path: Path,
) -> None:
    registry, champion = seeded_registry(tmp_path)
    manager = ChampionProbationManager(
        registry,
        store=ChampionProbationStore(tmp_path / "probation.json"),
        policy=ProbationPolicy(min_observations=2),
    )
    manager.start(champion)
    degraded = {
        "sharpe": 0.6,
        "sortino": 0.7,
        "max_drawdown": 0.12,
        "calmar": 0.7,
    }

    assert manager.observe(degraded).action == "continue"
    result = manager.observe(degraded)

    assert result.action == "rollback"
    assert "Sharpe degraded during probation" in result.reasons
    assert "Sortino degraded during probation" in result.reasons
    assert registry.active() is not None
    assert registry.active().version == "v1"


def test_probation_fails_closed_when_metrics_are_missing(tmp_path: Path) -> None:
    registry, champion = seeded_registry(tmp_path)
    manager = ChampionProbationManager(
        registry,
        store=ChampionProbationStore(tmp_path / "probation.json"),
    )
    manager.start(champion)

    result = manager.observe({"sharpe": 1.0})

    assert result.action == "rollback"
    assert "missing probation metrics" in result.reasons[0]
    assert registry.active() is not None
    assert registry.active().version == "v1"


def test_probation_rollback_records_model_failure(tmp_path: Path) -> None:
    registry, champion = seeded_registry(tmp_path)
    quarantine = ModelQuarantineStore(tmp_path / "quarantine.json")
    manager = ChampionProbationManager(
        registry,
        store=ChampionProbationStore(tmp_path / "probation.json"),
        quarantine_store=quarantine,
    )
    manager.start(champion)

    result = manager.observe(
        {
            "sharpe": 1.0,
            "sortino": 1.2,
            "max_drawdown": 0.18,
            "calmar": 1.1,
        },
        processed_bar=100,
    )

    record = quarantine.load()["v2"]
    assert result.action == "rollback"
    assert record.failures == 1
    assert record.next_eligible_bar > 100


def test_probation_success_clears_model_failures(tmp_path: Path) -> None:
    registry, champion = seeded_registry(tmp_path)
    quarantine = ModelQuarantineStore(tmp_path / "quarantine.json")
    quarantine.record_failure("v2", processed_bar=10, reason="old failure")
    manager = ChampionProbationManager(
        registry,
        store=ChampionProbationStore(tmp_path / "probation.json"),
        policy=ProbationPolicy(min_observations=1),
        quarantine_store=quarantine,
    )
    manager.start(champion)

    result = manager.observe(BASELINE, processed_bar=100)

    assert result.action == "pass"
    assert quarantine.load()["v2"].failures == 0

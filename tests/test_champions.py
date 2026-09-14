from pathlib import Path

from ai_trading.champions import ChampionRegistry
from ai_trading.model_quarantine import ModelQuarantineStore, QuarantinePolicy


def test_promote_and_rollback(tmp_path: Path) -> None:
    registry = ChampionRegistry(tmp_path / "champions.jsonl")
    first = registry.promote(
        version="v1",
        model_name="baseline",
        score=1.0,
        metrics={"sharpe": 1.0},
        config={"a": 1},
    )
    second = registry.promote(
        version="v2",
        model_name="ensemble",
        score=1.2,
        metrics={"sharpe": 1.2},
        config={"a": 2},
    )

    assert registry.active() == second
    rolled = registry.rollback()
    assert rolled.version == first.version
    assert registry.active() == rolled



def test_guarded_promotion_keeps_existing_champion_on_regression(tmp_path: Path) -> None:
    registry = ChampionRegistry(tmp_path / "champions.jsonl")
    first = registry.promote(
        version="v1",
        model_name="baseline",
        score=1.0,
        metrics={
            "sharpe": 1.0,
            "sortino": 1.2,
            "max_drawdown": 0.10,
            "calmar": 1.1,
        },
        config={"a": 1},
    )

    decision, promoted = registry.promote_if_qualified(
        version="v2",
        model_name="challenger",
        score=1.2,
        metrics={
            "sharpe": 1.2,
            "sortino": 1.3,
            "max_drawdown": 0.20,
            "calmar": 1.2,
        },
        config={"a": 2},
    )

    assert not decision.approved
    assert promoted is None
    assert registry.active() == first


def test_guarded_promotion_activates_qualified_challenger(tmp_path: Path) -> None:
    registry = ChampionRegistry(tmp_path / "champions.jsonl")
    registry.promote(
        version="v1",
        model_name="baseline",
        score=1.0,
        metrics={
            "sharpe": 1.0,
            "sortino": 1.2,
            "max_drawdown": 0.10,
            "calmar": 1.1,
        },
        config={"a": 1},
    )

    decision, promoted = registry.promote_if_qualified(
        version="v2",
        model_name="challenger",
        score=1.1,
        metrics={
            "sharpe": 1.1,
            "sortino": 1.3,
            "max_drawdown": 0.09,
            "calmar": 1.2,
        },
        config={"a": 2},
    )

    assert decision.approved
    assert promoted is not None
    assert registry.active() == promoted



def test_guarded_promotion_rejects_quarantined_version(tmp_path: Path) -> None:
    registry = ChampionRegistry(tmp_path / "champions.jsonl")
    registry.promote(
        version="v1",
        model_name="baseline",
        score=1.0,
        metrics={
            "sharpe": 1.0,
            "sortino": 1.2,
            "max_drawdown": 0.10,
            "calmar": 1.1,
        },
        config={},
    )
    quarantine = ModelQuarantineStore(tmp_path / "quarantine.json")
    policy = QuarantinePolicy(failures_before_quarantine=1)
    quarantine.record_failure(
        "v2",
        processed_bar=10,
        reason="probation rollback",
        policy=policy,
    )

    decision, promoted = registry.promote_if_qualified(
        version="v2",
        model_name="challenger",
        score=1.2,
        metrics={
            "sharpe": 1.2,
            "sortino": 1.4,
            "max_drawdown": 0.08,
            "calmar": 1.3,
        },
        config={},
        quarantine_store=quarantine,
        processed_bar=1000,
    )

    assert not decision.approved
    assert promoted is None
    assert "quarantined" in decision.reasons[0]
    assert registry.active() is not None
    assert registry.active().version == "v1"

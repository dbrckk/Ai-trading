from pathlib import Path

from ai_trading.champions import ChampionRegistry


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

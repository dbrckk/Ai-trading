from pathlib import Path

from ai_trading.expert_pool import ExpertPoolStore, ExpertRecord
from ai_trading.generation_rollback import rollback_generation
from ai_trading.generations import GenerationStore


def test_generation_rollback_restores_previous_active_set(tmp_path: Path) -> None:
    pool = ExpertPoolStore(tmp_path / "pool.json")
    generations = GenerationStore(
        tmp_path / "lineage.json",
        tmp_path / "generations.jsonl",
    )
    pool.save(
        {
            "a": ExpertRecord("a", "trend", "challenger", score=0.7),
            "b": ExpertRecord("b", "range", "active", score=0.8),
        }
    )
    generations.snapshot(["a"], 0.6)
    generations.snapshot(["b"], 0.8)

    result = rollback_generation(pool, generations)
    records = pool.load()
    assert result.active_experts == ("a",)
    assert records["a"].status == "active"
    assert records["b"].status == "challenger"

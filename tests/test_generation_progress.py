import pytest

from ai_trading.generation_progress import compare_generations
from ai_trading.generations import GenerationSnapshot


def test_generation_progress_detects_improvement() -> None:
    previous = GenerationSnapshot(
        generation=1,
        active_experts=("a",),
        portfolio_score=0.6,
        created_at_utc="x",
    )
    current = GenerationSnapshot(
        generation=2,
        active_experts=("b",),
        portfolio_score=0.8,
        created_at_utc="y",
    )
    progress = compare_generations(previous, current)
    assert progress.improved
    assert progress.score_delta == pytest.approx(0.2)

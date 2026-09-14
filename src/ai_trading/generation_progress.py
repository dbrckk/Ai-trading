from __future__ import annotations

from dataclasses import dataclass

from .generations import GenerationSnapshot


@dataclass(frozen=True)
class GenerationProgress:
    score_delta: float
    improved: bool
    current_generation: int
    previous_generation: int


def compare_generations(
    previous: GenerationSnapshot,
    current: GenerationSnapshot,
    *,
    min_improvement: float = 0.0,
) -> GenerationProgress:
    delta = float(current.portfolio_score - previous.portfolio_score)
    return GenerationProgress(
        score_delta=delta,
        improved=delta > min_improvement,
        current_generation=current.generation,
        previous_generation=previous.generation,
    )

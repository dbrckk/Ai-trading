from __future__ import annotations

from dataclasses import dataclass

from .expert_diversity import DiversityReport


@dataclass(frozen=True)
class GlobalGenerationDecision:
    accept: bool
    reason: str


def evaluate_global_generation(
    *,
    previous_score: float,
    current_score: float,
    diversity: DiversityReport,
    min_score_improvement: float = 0.0,
) -> GlobalGenerationDecision:
    if not diversity.diversified:
        return GlobalGenerationDecision(False, "cross-asset diversification constraint failed")
    if current_score <= previous_score + min_score_improvement:
        return GlobalGenerationDecision(False, "global portfolio score did not improve")
    return GlobalGenerationDecision(True, "global portfolio improved with diversification")

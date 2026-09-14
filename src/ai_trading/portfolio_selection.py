from __future__ import annotations

from dataclasses import dataclass

from .marginal_alpha import MarginalAlphaReport


@dataclass(frozen=True)
class ReplacementDecision:
    replace: bool
    reason: str


def evaluate_portfolio_replacement(
    challenger: MarginalAlphaReport,
    *,
    incumbent_score: float,
    challenger_score: float,
    min_score_improvement: float = 0.02,
) -> ReplacementDecision:
    if not challenger.improves_portfolio:
        return ReplacementDecision(False, "challenger does not improve full portfolio")
    if challenger_score < incumbent_score + min_score_improvement:
        return ReplacementDecision(False, "insufficient expert score improvement")
    return ReplacementDecision(True, "challenger improves portfolio and expert score")

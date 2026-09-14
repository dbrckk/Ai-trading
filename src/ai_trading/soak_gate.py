from __future__ import annotations

from dataclasses import dataclass

from .soak import SoakResult


@dataclass(frozen=True)
class SoakQualificationPolicy:
    min_cycles: int = 50
    min_success_ratio: float = 0.98
    max_failures: int = 2
    max_drawdown: float = 0.10
    disallowed_governor_verdicts: tuple[str, ...] = ("HALT",)


@dataclass(frozen=True)
class SoakQualification:
    passed: bool
    success_ratio: float
    reasons: tuple[str, ...]


def evaluate_soak_qualification(
    result: SoakResult,
    policy: SoakQualificationPolicy | None = None,
) -> SoakQualification:
    policy = policy or SoakQualificationPolicy()
    reasons: list[str] = []

    success_ratio = (
        result.successes / result.cycles
        if result.cycles > 0
        else 0.0
    )

    if result.cycles < policy.min_cycles:
        reasons.append("insufficient soak cycles")
    if success_ratio < policy.min_success_ratio:
        reasons.append("success ratio below threshold")
    if result.failures > policy.max_failures:
        reasons.append("too many soak failures")
    if result.max_drawdown > policy.max_drawdown:
        reasons.append("soak drawdown exceeded threshold")
    if result.governor_verdict in policy.disallowed_governor_verdicts:
        reasons.append(f"governor ended in {result.governor_verdict}")

    return SoakQualification(
        passed=not reasons,
        success_ratio=float(success_ratio),
        reasons=tuple(reasons),
    )

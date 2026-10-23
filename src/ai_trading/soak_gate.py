from __future__ import annotations

from dataclasses import dataclass
from math import isfinite

from .soak import SoakResult


@dataclass(frozen=True)
class SoakQualificationPolicy:
    min_cycles: int = 50
    min_success_ratio: float = 0.98
    max_failures: int = 2
    max_drawdown: float = 0.10
    min_duration_seconds: float = 0.0
    disallowed_governor_verdicts: tuple[str, ...] = ("HALT",)

    def __post_init__(self) -> None:
        if self.min_cycles < 0 or self.max_failures < 0:
            raise ValueError("soak count thresholds must be non-negative")
        if not isfinite(self.min_success_ratio) or not 0.0 <= self.min_success_ratio <= 1.0:
            raise ValueError("min_success_ratio must be finite and in [0, 1]")
        if not isfinite(self.max_drawdown) or not 0.0 <= self.max_drawdown <= 1.0:
            raise ValueError("max_drawdown must be finite and in [0, 1]")
        if not isfinite(self.min_duration_seconds) or self.min_duration_seconds < 0:
            raise ValueError("min_duration_seconds must be finite and non-negative")


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

    if (
        result.cycles <= 0
        or result.successes < 0
        or result.failures < 0
        or result.successes + result.failures != result.cycles
    ):
        reasons.append("inconsistent soak cycle counts")
    if not isfinite(result.max_drawdown) or not 0.0 <= result.max_drawdown <= 1.0:
        reasons.append("invalid soak drawdown")
    if not isfinite(result.duration_seconds) or result.duration_seconds < 0:
        reasons.append("invalid soak duration")
    if (
        result.final_equity is not None
        and (not isfinite(result.final_equity) or result.final_equity <= 0)
    ) or (result.successes > 0 and result.final_equity is None):
        reasons.append("invalid soak final equity")
    if result.min_equity is not None and (
        not isfinite(result.min_equity) or result.min_equity <= 0
    ):
        reasons.append("invalid soak minimum equity")
    if result.cycles < policy.min_cycles:
        reasons.append("insufficient soak cycles")
    if success_ratio < policy.min_success_ratio:
        reasons.append("success ratio below threshold")
    if result.failures > policy.max_failures:
        reasons.append("too many soak failures")
    if result.max_drawdown > policy.max_drawdown:
        reasons.append("soak drawdown exceeded threshold")
    if result.duration_seconds < policy.min_duration_seconds:
        reasons.append("insufficient soak duration")
    if result.governor_verdict in policy.disallowed_governor_verdicts:
        reasons.append(f"governor ended in {result.governor_verdict}")

    return SoakQualification(
        passed=not reasons,
        success_ratio=float(success_ratio),
        reasons=tuple(reasons),
    )

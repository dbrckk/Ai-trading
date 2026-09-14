from __future__ import annotations

from dataclasses import dataclass

from .readiness_score import ReadinessHistoryRecord


@dataclass(frozen=True)
class ReadinessTrendPolicy:
    window: int = 5
    max_decline: float = 5.0
    min_pass_ratio: float = 0.80


@dataclass(frozen=True)
class ReadinessTrend:
    status: str
    observations: int
    latest_score: float | None
    score_change: float
    pass_ratio: float
    reasons: tuple[str, ...]


def evaluate_readiness_trend(
    records: list[ReadinessHistoryRecord],
    policy: ReadinessTrendPolicy | None = None,
) -> ReadinessTrend:
    policy = policy or ReadinessTrendPolicy()
    recent = records[-policy.window :]
    if not recent:
        return ReadinessTrend(
            status="insufficient",
            observations=0,
            latest_score=None,
            score_change=0.0,
            pass_ratio=0.0,
            reasons=("readiness history missing",),
        )

    scores = [record.result.score for record in recent]
    score_change = scores[-1] - scores[0] if len(scores) > 1 else 0.0
    pass_ratio = sum(record.result.passed for record in recent) / len(recent)

    reasons: list[str] = []
    if len(recent) < policy.window:
        reasons.append("readiness trend window incomplete")
    if score_change < -policy.max_decline:
        reasons.append("readiness score trend declining")
    if pass_ratio < policy.min_pass_ratio:
        reasons.append("readiness pass ratio below trend threshold")

    return ReadinessTrend(
        status="degraded" if reasons else "stable",
        observations=len(recent),
        latest_score=scores[-1],
        score_change=float(score_change),
        pass_ratio=float(pass_ratio),
        reasons=tuple(reasons),
    )

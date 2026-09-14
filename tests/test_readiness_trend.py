from datetime import UTC, datetime, timedelta

from ai_trading.readiness_score import (
    ReadinessComponents,
    ReadinessHistoryRecord,
    evaluate_composite_readiness,
)
from ai_trading.readiness_trend import ReadinessTrendPolicy, evaluate_readiness_trend


def record(score: float, passed: bool = True, offset: int = 0) -> ReadinessHistoryRecord:
    result = evaluate_composite_readiness(
        ReadinessComponents(
            performance=score,
            robustness=score,
            reliability=score,
            recovery=score,
            data_quality=score,
            model_stability=score,
            execution_quality=score,
        )
    )
    result = type(result)(
        **{
            **result.__dict__,
            "passed": passed,
        }
    )
    return ReadinessHistoryRecord(
        created_at_utc=(datetime.now(UTC) + timedelta(minutes=offset)).isoformat(),
        result=result,
    )


def test_readiness_trend_is_stable_for_consistent_scores() -> None:
    trend = evaluate_readiness_trend(
        [record(92.0, offset=index) for index in range(5)]
    )

    assert trend.status == "stable"
    assert trend.pass_ratio == 1.0
    assert trend.score_change == 0.0


def test_readiness_trend_detects_declining_score() -> None:
    trend = evaluate_readiness_trend(
        [
            record(98.0, offset=0),
            record(96.0, offset=1),
            record(94.0, offset=2),
            record(91.0, offset=3),
            record(90.0, offset=4),
        ],
        ReadinessTrendPolicy(max_decline=5.0),
    )

    assert trend.status == "degraded"
    assert trend.score_change == -8.0
    assert "readiness score trend declining" in trend.reasons


def test_readiness_trend_requires_full_window() -> None:
    trend = evaluate_readiness_trend([record(95.0), record(95.0)])

    assert trend.status == "degraded"
    assert "readiness trend window incomplete" in trend.reasons

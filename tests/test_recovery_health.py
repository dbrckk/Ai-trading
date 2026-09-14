from pathlib import Path

from ai_trading.lifecycle_log import LifecycleEventLog
from ai_trading.recovery_health import RecoveryHealthPolicy, evaluate_recovery_health


def test_recovery_health_is_healthy_for_shallow_success(tmp_path: Path) -> None:
    lifecycle = LifecycleEventLog(tmp_path / "lifecycle.jsonl")
    lifecycle.append(
        event="recovery_succeeded",
        version="",
        model_name="",
        metadata={"fallback_depth": 1},
    )

    health = evaluate_recovery_health(lifecycle)

    assert health.status == "healthy"
    assert health.recent_attempts == 1
    assert health.recent_failures == 0
    assert health.max_fallback_depth == 1


def test_recovery_health_degrades_on_failures_or_deep_fallback(
    tmp_path: Path,
) -> None:
    lifecycle = LifecycleEventLog(tmp_path / "lifecycle.jsonl")
    lifecycle.append(
        event="recovery_failed",
        version="",
        model_name="",
        failure_type="technical_failure",
        metadata={"fallback_depth": 1},
    )
    lifecycle.append(
        event="recovery_succeeded",
        version="",
        model_name="",
        metadata={"fallback_depth": 4},
    )

    health = evaluate_recovery_health(
        lifecycle,
        RecoveryHealthPolicy(
            max_recent_failures=0,
            max_fallback_depth=2,
            recent_event_window=10,
        ),
    )

    assert health.status == "degraded"
    assert "too many recent recovery failures" in health.reasons
    assert "recovery fallback depth exceeds policy" in health.reasons

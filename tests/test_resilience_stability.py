from pathlib import Path

from ai_trading.lifecycle_log import LifecycleEventLog
from ai_trading.resilience_stability import (
    ResilienceStabilityPolicy,
    evaluate_resilience_stability,
)


def append_transition(log: LifecycleEventLog, from_mode: str, to_mode: str) -> None:
    log.append(
        event="resilience_transition",
        version="",
        model_name="",
        metadata={"from_mode": from_mode, "to_mode": to_mode},
    )


def test_detects_repeated_mode_oscillation(tmp_path: Path) -> None:
    log = LifecycleEventLog(tmp_path / "lifecycle.jsonl")
    sequence = ["NORMAL", "DEGRADED", "NORMAL", "DEGRADED", "NORMAL", "DEGRADED"]
    previous = "NORMAL"
    for mode in sequence:
        append_transition(log, previous, mode)
        previous = mode

    health = evaluate_resilience_stability(
        log,
        ResilienceStabilityPolicy(max_oscillations=3),
    )

    assert health.status == "degraded"
    assert health.oscillations >= 3
    assert "resilience mode oscillation threshold exceeded" in health.reasons


def test_detects_excessive_recovery_duration(tmp_path: Path) -> None:
    log = LifecycleEventLog(tmp_path / "lifecycle.jsonl")
    for _ in range(4):
        append_transition(log, "DEGRADED", "RECOVERY")

    health = evaluate_resilience_stability(
        log,
        ResilienceStabilityPolicy(max_recovery_streak_events=4),
    )

    assert health.status == "degraded"
    assert health.recovery_streak_events == 4


def test_detects_repeated_cooldowns(tmp_path: Path) -> None:
    log = LifecycleEventLog(tmp_path / "lifecycle.jsonl")
    for _ in range(3):
        append_transition(log, "HALT", "COOLDOWN")
        append_transition(log, "COOLDOWN", "NORMAL")

    health = evaluate_resilience_stability(
        log,
        ResilienceStabilityPolicy(max_cooldowns=3),
    )

    assert health.status == "degraded"
    assert health.cooldown_count == 3


def test_marks_extreme_transition_instability_critical(tmp_path: Path) -> None:
    log = LifecycleEventLog(tmp_path / "lifecycle.jsonl")
    previous = "NORMAL"
    for mode in [
        "DEGRADED",
        "NORMAL",
        "DEGRADED",
        "NORMAL",
        "DEGRADED",
        "NORMAL",
        "DEGRADED",
        "NORMAL",
        "DEGRADED",
    ]:
        append_transition(log, previous, mode)
        previous = mode

    health = evaluate_resilience_stability(
        log,
        ResilienceStabilityPolicy(max_oscillations=3),
    )

    assert health.status == "critical"

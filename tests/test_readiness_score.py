from pathlib import Path

from ai_trading.readiness_score import (
    ReadinessComponents,
    ReadinessHistoryStore,
    ReadinessPolicy,
    ReadinessWeights,
    evaluate_composite_readiness,
)


def test_composite_readiness_passes_strong_profile() -> None:
    result = evaluate_composite_readiness(
        ReadinessComponents(
            performance=95.0,
            robustness=92.0,
            reliability=98.0,
            recovery=94.0,
            data_quality=99.0,
            model_stability=93.0,
            execution_quality=91.0,
        )
    )

    assert result.passed
    assert result.score >= 90.0
    assert len(result.evidence_hash) == 64


def test_composite_readiness_fails_weak_component_even_if_average_is_high() -> None:
    result = evaluate_composite_readiness(
        ReadinessComponents(
            performance=99.0,
            robustness=99.0,
            reliability=99.0,
            recovery=99.0,
            data_quality=99.0,
            model_stability=50.0,
            execution_quality=99.0,
        )
    )

    assert not result.passed
    assert "model_stability below minimum component threshold" in result.reasons


def test_composite_readiness_hash_is_deterministic() -> None:
    components = ReadinessComponents(
        performance=90.0,
        robustness=90.0,
        reliability=90.0,
        recovery=90.0,
        data_quality=90.0,
        model_stability=90.0,
        execution_quality=90.0,
    )
    first = evaluate_composite_readiness(components)
    second = evaluate_composite_readiness(components)

    assert first.evidence_hash == second.evidence_hash


def test_custom_weights_are_normalized() -> None:
    result = evaluate_composite_readiness(
        ReadinessComponents(
            performance=100.0,
            robustness=80.0,
            reliability=80.0,
            recovery=80.0,
            data_quality=80.0,
            model_stability=80.0,
            execution_quality=80.0,
        ),
        weights=ReadinessWeights(
            performance=2.0,
            robustness=1.0,
            reliability=1.0,
            recovery=1.0,
            data_quality=1.0,
            model_stability=1.0,
            execution_quality=1.0,
        ),
        policy=ReadinessPolicy(min_score=0.0, min_component=0.0),
    )

    assert result.score == 82.5


def test_readiness_history_round_trip(tmp_path: Path) -> None:
    store = ReadinessHistoryStore(tmp_path / "readiness.jsonl")
    result = evaluate_composite_readiness(
        ReadinessComponents(
            performance=95.0,
            robustness=95.0,
            reliability=95.0,
            recovery=95.0,
            data_quality=95.0,
            model_stability=95.0,
            execution_quality=95.0,
        )
    )

    saved = store.append(result)
    loaded = store.list()

    assert len(loaded) == 1
    assert loaded[0].created_at_utc == saved.created_at_utc
    assert loaded[0].result == result

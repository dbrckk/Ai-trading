from ai_trading.mtf_shadow_quality import compare_mtf_shadow_audit_payloads


def river_payload(execution_time: str, side: int, confidence: float) -> dict[str, object]:
    return {
        "execution_time": execution_time,
        "prediction": {
            "side": side,
            "confidence": confidence,
            "probabilities": {},
        },
    }


def mtf_payload(
    attached_execution_time: str,
    evaluated_execution_time: str,
    side: int,
    confidence: float,
    realized_label: int,
) -> dict[str, object]:
    return {
        "execution_time": attached_execution_time,
        "prediction": {
            "side": 0,
            "confidence": 0.55,
            "probabilities": {},
        },
        "mtf_shadow_challenger": {
            "execution_time": evaluated_execution_time,
            "prediction": {
                "side": side,
                "confidence": confidence,
                "probabilities": {},
            },
            "realized_label": realized_label,
        },
    }


def test_mtf_quality_joins_river_prediction_by_delayed_execution_time() -> None:
    payloads = [
        river_payload("t1", 1, 0.70),
        river_payload("t2", 1, 0.75),
        river_payload("t3", -1, 0.80),
        river_payload("t4", 0, 0.60),
        river_payload("t5", 1, 0.85),
        mtf_payload("t4", "t1", 1, 0.85, 1),
        mtf_payload("t5", "t2", 0, 0.70, 0),
        mtf_payload("t6", "t3", -1, 0.88, -1),
        mtf_payload("t7", "t4", 0, 0.76, 0),
        mtf_payload("t8", "t5", -1, 0.80, -1),
    ]

    comparison = compare_mtf_shadow_audit_payloads(payloads)

    assert comparison.observations == 5
    assert comparison.river.observations == 5
    assert comparison.challenger.observations == 5
    assert comparison.challenger.accuracy > comparison.river.accuracy
    assert comparison.score_delta > 0.0
    assert comparison.directional_observations == 3
    assert comparison.directional_rate == 0.6
    assert comparison.long_labels == 1
    assert comparison.flat_labels == 2
    assert comparison.short_labels == 2


def test_mtf_quality_deduplicates_same_evaluated_execution() -> None:
    payloads = [
        river_payload("t1", 1, 0.70),
        mtf_payload("t3", "t1", -1, 0.60, -1),
        mtf_payload("t4", "t1", 1, 0.90, 1),
    ]

    comparison = compare_mtf_shadow_audit_payloads(payloads)

    assert comparison.observations == 1
    assert comparison.directional_observations == 1
    assert comparison.long_labels == 1
    assert comparison.flat_labels == 0
    assert comparison.short_labels == 0



def test_mtf_quality_exposes_flat_only_evidence() -> None:
    payloads = [
        river_payload("t1", 0, 0.60),
        river_payload("t2", 0, 0.61),
        mtf_payload("t4", "t1", 0, 0.70, 0),
        mtf_payload("t5", "t2", 0, 0.71, 0),
    ]

    comparison = compare_mtf_shadow_audit_payloads(payloads)

    assert comparison.observations == 2
    assert comparison.directional_observations == 0
    assert comparison.directional_rate == 0.0
    assert comparison.flat_labels == 2

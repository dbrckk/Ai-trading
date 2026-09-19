from ai_trading.shadow_quality import compare_shadow_audit_payloads


def payload(
    river_side: int,
    river_confidence: float,
    challenger_side: int,
    challenger_confidence: float,
    realized_label: int,
) -> dict[str, object]:
    return {
        "prediction": {
            "side": river_side,
            "confidence": river_confidence,
            "probabilities": {},
        },
        "shadow_challenger": {
            "prediction": {
                "side": challenger_side,
                "confidence": challenger_confidence,
                "probabilities": {},
            },
            "realized_label": realized_label,
        },
    }


def test_shadow_quality_compares_both_models_on_identical_labels() -> None:
    comparison = compare_shadow_audit_payloads(
        [
            payload(1, 0.8, 1, 0.9, 1),
            payload(1, 0.7, 0, 0.6, 0),
            payload(-1, 0.8, -1, 0.8, -1),
            payload(0, 0.6, 0, 0.7, 0),
            payload(1, 0.9, -1, 0.7, -1),
        ]
    )

    assert comparison.observations == 5
    assert comparison.river.observations == 5
    assert comparison.challenger.observations == 5
    assert comparison.challenger.accuracy > comparison.river.accuracy
    assert comparison.score_delta > 0.0


def test_shadow_quality_ignores_unusable_audit_rows() -> None:
    comparison = compare_shadow_audit_payloads(
        [
            {},
            {"prediction": {"side": 1, "confidence": 0.8}},
            payload(1, 0.8, 1, 0.9, 1),
        ]
    )

    assert comparison.observations == 1

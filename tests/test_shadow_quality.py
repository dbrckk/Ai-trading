import pandas as pd

from ai_trading.shadow_quality import compare_shadow_audit_payloads
from ai_trading.river_v2_shadow import compare_river_v2_forward_audit_payloads


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

    # Forward observations are stored one cycle *before* their outcomes.
    # Compare them with the same later audit record that holds the v1 side.
    audit_rows = []
    for i in range(5):
        signal = pd.Timestamp("2026-10-21T08:00:00+00:00") + pd.Timedelta(
            minutes=10 * i
        )
        side = -1 if i % 2 == 0 else 1
        audit_rows.append(
            {
                "_audit_timestamp_utc": str(signal + pd.Timedelta(minutes=7)),
                "river_v2_shadow": {
                    "signal_time": str(signal),
                    "signal_close": 100.0,
                    "observed_at_utc": str(signal + pd.Timedelta(minutes=6)),
                    "model_format": "joblib-river-ovr-v2",
                    "model_version": 2,
                    "horizon_bars": 1,
                    "return_threshold": 0.001,
                    "min_confidence": 0.56,
                    "prediction": {"side": side, "confidence": 0.85},
                }
            }
        )
        audit_rows.append(
            {
                "signal_time": str(signal),
                "execution_time": str(signal + pd.Timedelta(minutes=5)),
                "execution_close": 99.5 if side < 0 else 100.5,
                "prediction": {"side": 0, "confidence": 0.70},
            }
        )
    forward = compare_river_v2_forward_audit_payloads(audit_rows)
    assert forward.observations == 5
    assert forward.pending == 0
    assert forward.short_predictions == 3
    assert forward.river_v2.accuracy == 1.0
    assert forward.river.accuracy == 0.0
    assert forward.score_delta is not None and forward.score_delta > 0


def test_shadow_quality_ignores_unusable_audit_rows() -> None:
    comparison = compare_shadow_audit_payloads(
        [
            {},
            {"prediction": {"side": 1, "confidence": 0.8}},
            payload(1, 0.8, 1, 0.9, 1),
        ]
    )

    assert comparison.observations == 1

    # No hindsight: malformed, stale or not-yet-matured samples cannot
    # manufacture additional v2 forward evidence.
    forward = compare_river_v2_forward_audit_payloads(
        [
            {"river_v2_shadow": {"signal_time": "2026-10-21T09:00:00+00:00"}},
            {"signal_time": "2026-10-21T09:00:00+00:00",
             "execution_time": "2026-10-21T09:05:00+00:00",
             "execution_close": 100,
             "prediction": {"side": 1, "confidence": 0.9}},
        ]
    )
    assert forward.observations == 0
    assert forward.score_delta is None

from ai_trading.confidence_calibration import conservatively_calibrate_prediction
from ai_trading.model import Prediction
from ai_trading.quality_store import QualityRecord


def test_calibration_shrinks_overconfident_prediction() -> None:
    record = QualityRecord(
        predictions=[1] * 20,
        confidences=[0.9] * 20,
        labels=[1] * 4 + [-1] * 16,
    )
    prediction = Prediction(
        side=1,
        confidence=0.9,
        probabilities={-1: 0.05, 0: 0.05, 1: 0.90},
    )

    calibrated, report = conservatively_calibrate_prediction(
        prediction,
        record,
    )

    assert calibrated.confidence < prediction.confidence
    assert report.expected_calibration_error > 0.0
    assert abs(sum(calibrated.probabilities.values()) - 1.0) < 1e-9


def test_calibration_leaves_short_history_unchanged() -> None:
    record = QualityRecord(
        predictions=[1] * 3,
        confidences=[0.8] * 3,
        labels=[1, 1, -1],
    )
    prediction = Prediction(
        side=1,
        confidence=0.8,
        probabilities={-1: 0.1, 0: 0.1, 1: 0.8},
    )

    calibrated, _ = conservatively_calibrate_prediction(prediction, record)
    assert calibrated == prediction

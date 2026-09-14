from ai_trading.calibration_routing import calibration_weight_multiplier


def test_calibration_penalty_reduces_weight_when_ece_is_high() -> None:
    good = calibration_weight_multiplier(ece=0.02, observations=100)
    bad = calibration_weight_multiplier(ece=0.30, observations=100)
    assert bad < good


def test_calibration_penalty_waits_for_enough_observations() -> None:
    weight = calibration_weight_multiplier(ece=0.50, observations=5)
    assert weight == 1.0

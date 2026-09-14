from ai_trading.regime_validation import validate_regime_returns


def test_regime_validation_passes_diversified_profile() -> None:
    result = validate_regime_returns(
        {
            "bull_normal_vol": 0.12,
            "bear_high_vol": 0.03,
            "sideways_normal_vol": -0.02,
        },
        min_regimes=2,
        min_profitable_fraction=0.5,
        worst_regime_floor=-0.10,
    )
    assert result.valid


def test_regime_validation_rejects_concentrated_profile() -> None:
    result = validate_regime_returns(
        {"bull_normal_vol": 0.20},
        min_regimes=2,
    )
    assert not result.valid

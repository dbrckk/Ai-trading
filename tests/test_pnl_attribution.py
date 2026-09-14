from ai_trading.pnl_attribution import attribute_pnl


def test_pnl_attribution_handles_long_and_short() -> None:
    result = attribute_pnl(
        previous_prices={"A": 100.0, "B": 50.0},
        current_prices={"A": 105.0, "B": 45.0},
        units={"A": 10.0, "B": -20.0},
        starting_equity=100_000.0,
    )
    assert result["A"].pnl == 50.0
    assert result["B"].pnl == 100.0
    assert result["A"].return_contribution == 0.0005

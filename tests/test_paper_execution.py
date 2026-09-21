import math

import pytest

from ai_trading.paper_execution import calculate_rebalance_fill


def test_rebalance_fill_handles_signed_target_and_flip() -> None:
    fill = calculate_rebalance_fill(
        current_units=2.0,
        target_notional=-1_000.0,
        price=100.0,
        transaction_cost_bps=2.0,
        slippage_bps=1.0,
    )

    assert fill.desired_units == pytest.approx(-10.0)
    assert fill.delta_units == pytest.approx(-12.0)
    assert fill.gross_turnover == pytest.approx(1_200.0)
    assert fill.costs == pytest.approx(0.36)


def test_rebalance_fill_flattening_charges_turnover_costs() -> None:
    fill = calculate_rebalance_fill(
        current_units=5.0,
        target_notional=0.0,
        price=50.0,
        transaction_cost_bps=2.0,
        slippage_bps=1.0,
    )

    assert fill.desired_units == 0.0
    assert fill.delta_units == -5.0
    assert fill.gross_turnover == pytest.approx(250.0)
    assert fill.costs == pytest.approx(0.075)


@pytest.mark.parametrize("price", [0.0, -1.0])
def test_rebalance_fill_rejects_non_positive_prices(price: float) -> None:
    with pytest.raises(ValueError, match="price"):
        calculate_rebalance_fill(
            current_units=0.0,
            target_notional=1_000.0,
            price=price,
            transaction_cost_bps=2.0,
            slippage_bps=1.0,
        )


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("current_units", math.nan),
        ("target_notional", math.inf),
        ("price", math.nan),
        ("transaction_cost_bps", math.inf),
        ("slippage_bps", math.nan),
    ],
)
def test_rebalance_fill_rejects_non_finite_inputs(field: str, value: float) -> None:
    kwargs = {
        "current_units": 0.0,
        "target_notional": 1_000.0,
        "price": 100.0,
        "transaction_cost_bps": 2.0,
        "slippage_bps": 1.0,
    }
    kwargs[field] = value

    with pytest.raises(ValueError, match=field):
        calculate_rebalance_fill(**kwargs)


def test_rebalance_fill_rejects_negative_execution_costs() -> None:
    with pytest.raises(ValueError, match="costs"):
        calculate_rebalance_fill(
            current_units=0.0,
            target_notional=1_000.0,
            price=100.0,
            transaction_cost_bps=-1.0,
            slippage_bps=0.0,
        )

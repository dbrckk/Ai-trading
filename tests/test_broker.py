import math

import pytest

from ai_trading.broker import PaperBroker
from ai_trading.config import RiskConfig


def test_broker_resets_daily_loss_baseline_to_current_equity() -> None:
    broker = PaperBroker(RiskConfig())
    broker.state.cash = 90_000.0
    broker.state.units = 10.0
    broker.mark(100.0)

    broker.reset_day_start()

    assert broker.state.day_start_equity == broker.state.equity
    assert broker.state.day_start_equity == 91_000.0


@pytest.mark.parametrize("price", [0.0, -1.0, math.nan, math.inf, -math.inf])
def test_broker_rejects_invalid_mark_prices(price: float) -> None:
    broker = PaperBroker(RiskConfig())
    with pytest.raises(ValueError, match="price"):
        broker.mark(price)


@pytest.mark.parametrize("side", [-2, 2, 99])
def test_broker_rejects_invalid_sides(side: int) -> None:
    broker = PaperBroker(RiskConfig())
    with pytest.raises(ValueError, match="side"):
        broker.rebalance(side, 1_000.0, 100.0)


@pytest.mark.parametrize("notional", [-1.0, math.nan, math.inf])
def test_broker_rejects_invalid_target_notional(notional: float) -> None:
    broker = PaperBroker(RiskConfig())
    with pytest.raises(ValueError, match="target_notional"):
        broker.rebalance(1, notional, 100.0)


def test_opt_in_deadband_avoids_costly_same_side_micro_rebalances() -> None:
    broker = PaperBroker(RiskConfig(min_rebalance_fraction=0.005))
    opening = broker.rebalance(1, 10_000.0, 100.0)
    assert opening.gross_turnover == pytest.approx(10_000.0)

    micro = broker.rebalance(1, 10_200.0, 100.0)
    assert micro.gross_turnover == 0.0
    assert micro.costs == 0.0
    assert broker.state.units == pytest.approx(100.0)

    meaningful = broker.rebalance(1, 11_000.0, 100.0)
    assert meaningful.gross_turnover == pytest.approx(1_000.0)
    assert meaningful.costs > 0.0
    assert broker.state.units == pytest.approx(110.0)


def test_deadband_never_blocks_stop_exit_or_position_flip() -> None:
    broker = PaperBroker(RiskConfig(min_rebalance_fraction=1.0))
    broker.rebalance(1, 1_000.0, 100.0)

    flipped = broker.rebalance(-1, 1_000.0, 100.0)
    assert flipped.gross_turnover == pytest.approx(2_000.0)
    assert broker.state.units == pytest.approx(-10.0)

    exited = broker.rebalance(0, 0.0, 100.0)
    assert exited.gross_turnover == pytest.approx(1_000.0)
    assert broker.state.units == 0.0


def test_rebalance_deadband_is_disabled_by_default() -> None:
    broker = PaperBroker(RiskConfig())
    broker.rebalance(1, 10_000.0, 100.0)

    fill = broker.rebalance(1, 10_200.0, 100.0)
    assert fill.gross_turnover == pytest.approx(200.0)
    assert fill.costs > 0.0


@pytest.mark.parametrize("fraction", [-0.01, 1.01, math.nan, math.inf])
def test_invalid_rebalance_deadband_rejected(fraction: float) -> None:
    with pytest.raises(ValueError, match="min_rebalance_fraction"):
        RiskConfig(min_rebalance_fraction=fraction)

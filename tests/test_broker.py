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

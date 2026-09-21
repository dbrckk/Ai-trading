import json

import pytest

from ai_trading.config import RiskConfig
from ai_trading.paper_execution import calculate_rebalance_fill
from ai_trading.performance_metrics import calculate_performance_metrics
from ai_trading.runtime_state import RuntimeStateStore
from ai_trading.trade_journal import TradeSnapshot


def trade(pnl: float, *, pnl_known: bool | None = None) -> TradeSnapshot:
    return TradeSnapshot(
        timestamp_utc="2026-09-21T18:00:00+00:00",
        symbol="GC=F",
        side="BUY",
        quantity=1.0,
        price=100.0,
        status="PAPER_FILLED",
        pnl=pnl,
        pnl_known=pnl_known,
    )


def test_opening_position_sets_cost_basis_and_realizes_only_costs() -> None:
    fill = calculate_rebalance_fill(
        current_units=0.0,
        current_average_entry_price=0.0,
        target_notional=1_000.0,
        price=100.0,
        transaction_cost_bps=2.0,
        slippage_bps=1.0,
    )

    assert fill.desired_units == pytest.approx(10.0)
    assert fill.realized_gross_pnl == pytest.approx(0.0)
    assert fill.realized_net_pnl == pytest.approx(-0.30)
    assert fill.next_average_entry_price == pytest.approx(100.0)


def test_adding_to_position_updates_weighted_average_entry() -> None:
    fill = calculate_rebalance_fill(
        current_units=10.0,
        current_average_entry_price=100.0,
        target_notional=2_200.0,
        price=110.0,
        transaction_cost_bps=2.0,
        slippage_bps=1.0,
    )

    assert fill.desired_units == pytest.approx(20.0)
    assert fill.next_average_entry_price == pytest.approx(105.0)
    assert fill.realized_gross_pnl == pytest.approx(0.0)


def test_reducing_long_realizes_price_move_less_costs() -> None:
    fill = calculate_rebalance_fill(
        current_units=10.0,
        current_average_entry_price=100.0,
        target_notional=500.0,
        price=120.0,
        transaction_cost_bps=2.0,
        slippage_bps=1.0,
    )

    assert fill.realized_gross_pnl == pytest.approx((10.0 - 500.0 / 120.0) * 20.0)
    assert fill.realized_net_pnl == pytest.approx(fill.realized_gross_pnl - fill.costs)
    assert fill.next_average_entry_price == pytest.approx(100.0)


def test_reducing_short_realizes_short_profit() -> None:
    fill = calculate_rebalance_fill(
        current_units=-10.0,
        current_average_entry_price=100.0,
        target_notional=-400.0,
        price=80.0,
        transaction_cost_bps=2.0,
        slippage_bps=1.0,
    )

    assert fill.realized_gross_pnl == pytest.approx(100.0)
    assert fill.realized_net_pnl == pytest.approx(99.88)
    assert fill.next_average_entry_price == pytest.approx(100.0)


def test_position_flip_realizes_old_side_and_resets_cost_basis() -> None:
    fill = calculate_rebalance_fill(
        current_units=10.0,
        current_average_entry_price=100.0,
        target_notional=-1_200.0,
        price=120.0,
        transaction_cost_bps=2.0,
        slippage_bps=1.0,
    )

    assert fill.desired_units == pytest.approx(-10.0)
    assert fill.realized_gross_pnl == pytest.approx(200.0)
    assert fill.realized_net_pnl == pytest.approx(199.28)
    assert fill.next_average_entry_price == pytest.approx(120.0)


def test_legacy_position_without_cost_basis_marks_realized_pnl_unknown() -> None:
    fill = calculate_rebalance_fill(
        current_units=10.0,
        current_average_entry_price=0.0,
        target_notional=0.0,
        price=120.0,
        transaction_cost_bps=2.0,
        slippage_bps=1.0,
    )

    assert fill.realized_gross_pnl is None
    assert fill.realized_net_pnl is None
    assert fill.next_average_entry_price == 0.0


def test_performance_excludes_unknown_legacy_pnl_but_counts_trade() -> None:
    metrics = calculate_performance_metrics(
        (
            trade(5.0, pnl_known=True),
            trade(0.0, pnl_known=False),
            trade(0.0, pnl_known=True),
        )
    )

    assert metrics.trade_count == 3
    assert metrics.pnl_observations == 2
    assert metrics.realized_pnl == 5.0
    assert metrics.average_pnl == pytest.approx(2.5)
    assert metrics.profit_factor == float("inf")


def test_trade_snapshot_defaults_legacy_zero_pnl_to_unknown() -> None:
    assert trade(0.0).pnl_known is False
    assert trade(1.0).pnl_known is True


def test_runtime_state_loads_legacy_json_without_cost_basis(tmp_path) -> None:
    path = tmp_path / "state.json"
    path.write_text(
        json.dumps(
            {
                "cash": 99_000.0,
                "units": 2.0,
                "last_price": 100.0,
                "peak_equity": 100_100.0,
                "day_start_equity": 100_000.0,
                "last_processed": "2026-01-01",
                "processed_bars": 5,
                "last_learning_cycle_bar": 0,
            }
        ),
        encoding="utf-8",
    )

    state = RuntimeStateStore(path).load(RiskConfig().starting_cash)

    assert state.average_entry_price == 0.0

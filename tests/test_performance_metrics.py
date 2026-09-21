from ai_trading.performance_metrics import calculate_performance_metrics
from ai_trading.trade_journal import TradeSnapshot


def _trade(pnl: float) -> TradeSnapshot:
    return TradeSnapshot(
        timestamp_utc="2026-09-17T10:00:00+00:00",
        symbol="GC=F",
        side="BUY",
        quantity=0.25,
        price=3650.0,
        status="PAPER_FILLED",
        pnl=pnl,
        pnl_known=True,
    )


def test_performance_metrics_empty_history() -> None:
    metrics = calculate_performance_metrics(())

    assert metrics.trade_count == 0
    assert metrics.pnl_observations == 0
    assert metrics.realized_pnl == 0.0
    assert metrics.average_pnl == 0.0
    assert metrics.gross_profit == 0.0
    assert metrics.gross_loss == 0.0
    assert metrics.profit_factor is None
    assert metrics.max_drawdown == 0.0


def test_performance_metrics_profit_factor_and_average() -> None:
    metrics = calculate_performance_metrics(
        (_trade(10.0), _trade(-4.0), _trade(6.0), _trade(0.0))
    )

    assert metrics.trade_count == 4
    assert metrics.pnl_observations == 4
    assert metrics.realized_pnl == 12.0
    assert metrics.average_pnl == 3.0
    assert metrics.gross_profit == 16.0
    assert metrics.gross_loss == 4.0
    assert metrics.profit_factor == 4.0


def test_performance_metrics_max_drawdown_uses_cumulative_realized_pnl() -> None:
    metrics = calculate_performance_metrics(
        (_trade(20.0), _trade(-5.0), _trade(-30.0), _trade(10.0))
    )

    assert metrics.max_drawdown == 35.0


def test_performance_metrics_profit_factor_is_infinite_without_losses() -> None:
    metrics = calculate_performance_metrics((_trade(5.0), _trade(7.0)))

    assert metrics.profit_factor == float("inf")



def test_performance_payload_marks_unmeasured_history_unavailable() -> None:
    from ai_trading.performance_metrics import (
        performance_metrics_from_totals,
        performance_payload,
    )

    metrics = performance_metrics_from_totals(
        trade_count=12,
        pnl_observations=0,
        realized_pnl=0.0,
        gross_profit=0.0,
        gross_loss=0.0,
        max_drawdown=0.0,
    )

    assert performance_payload(metrics) == {
        "available": False,
        "trade_count": 12,
        "pnl_observations": 0,
        "pnl_coverage": 0.0,
        "realized_pnl": None,
        "average_pnl": None,
        "gross_profit": None,
        "gross_loss": None,
        "profit_factor": None,
        "profit_factor_infinite": False,
        "max_drawdown": None,
    }


def test_performance_payload_serializes_infinite_profit_factor_explicitly() -> None:
    from ai_trading.performance_metrics import (
        performance_metrics_from_totals,
        performance_payload,
    )

    metrics = performance_metrics_from_totals(
        trade_count=2,
        pnl_observations=2,
        realized_pnl=5.0,
        gross_profit=5.0,
        gross_loss=0.0,
        max_drawdown=0.0,
    )
    payload = performance_payload(metrics)

    assert payload["available"] is True
    assert payload["profit_factor"] is None
    assert payload["profit_factor_infinite"] is True

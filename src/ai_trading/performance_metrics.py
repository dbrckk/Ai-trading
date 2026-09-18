from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from .trade_journal import TradeSnapshot


@dataclass(frozen=True)
class TradePerformanceMetrics:
    trade_count: int
    realized_pnl: float
    average_pnl: float
    gross_profit: float
    gross_loss: float
    profit_factor: float | None
    max_drawdown: float


def performance_metrics_from_totals(
    *,
    trade_count: int,
    realized_pnl: float,
    gross_profit: float,
    gross_loss: float,
    max_drawdown: float,
) -> TradePerformanceMetrics:
    average_pnl = realized_pnl / trade_count if trade_count else 0.0
    if gross_loss > 0.0:
        profit_factor: float | None = gross_profit / gross_loss
    elif gross_profit > 0.0:
        profit_factor = float("inf")
    else:
        profit_factor = None
    return TradePerformanceMetrics(
        trade_count=trade_count,
        realized_pnl=realized_pnl,
        average_pnl=average_pnl,
        gross_profit=gross_profit,
        gross_loss=gross_loss,
        profit_factor=profit_factor,
        max_drawdown=max_drawdown,
    )


def calculate_performance_metrics(
    trades: Iterable[TradeSnapshot],
) -> TradePerformanceMetrics:
    pnls = tuple(trade.pnl for trade in trades)
    realized_pnl = sum(pnls)
    gross_profit = sum(pnl for pnl in pnls if pnl > 0.0)
    gross_loss = -sum(pnl for pnl in pnls if pnl < 0.0)

    cumulative_pnl = 0.0
    peak_pnl = 0.0
    max_drawdown = 0.0
    for pnl in pnls:
        cumulative_pnl += pnl
        peak_pnl = max(peak_pnl, cumulative_pnl)
        max_drawdown = max(max_drawdown, peak_pnl - cumulative_pnl)

    return performance_metrics_from_totals(
        trade_count=len(pnls),
        realized_pnl=realized_pnl,
        gross_profit=gross_profit,
        gross_loss=gross_loss,
        max_drawdown=max_drawdown,
    )

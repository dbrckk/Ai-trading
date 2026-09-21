from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from .trade_journal import TradeSnapshot


@dataclass(frozen=True)
class TradePerformanceMetrics:
    trade_count: int
    pnl_observations: int
    realized_pnl: float
    average_pnl: float
    gross_profit: float
    gross_loss: float
    profit_factor: float | None
    max_drawdown: float


def performance_metrics_from_totals(
    *,
    trade_count: int,
    pnl_observations: int | None = None,
    realized_pnl: float,
    gross_profit: float,
    gross_loss: float,
    max_drawdown: float,
) -> TradePerformanceMetrics:
    observations = trade_count if pnl_observations is None else pnl_observations
    if observations < 0 or observations > trade_count:
        raise ValueError("pnl_observations must be between 0 and trade_count")
    average_pnl = realized_pnl / observations if observations else 0.0
    profit_factor: float | None
    if observations == 0:
        profit_factor = None
    elif gross_loss > 0.0:
        profit_factor = gross_profit / gross_loss
    elif gross_profit > 0.0:
        profit_factor = float("inf")
    else:
        profit_factor = None
    return TradePerformanceMetrics(
        trade_count=trade_count,
        pnl_observations=observations,
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
    snapshots = tuple(trades)
    pnls = tuple(trade.pnl for trade in snapshots if trade.pnl_known is True)
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
        trade_count=len(snapshots),
        pnl_observations=len(pnls),
        realized_pnl=realized_pnl,
        gross_profit=gross_profit,
        gross_loss=gross_loss,
        max_drawdown=max_drawdown,
    )

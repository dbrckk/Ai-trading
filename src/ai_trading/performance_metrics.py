from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, replace
from math import isfinite

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




def resolved_portfolio_allocations(
    runtime_keys: tuple[str, ...],
    allocations: tuple[float, ...] | None,
) -> tuple[float, ...]:
    """Match normalized paper sleeves to the weights used in portfolio equity."""
    if len(set(runtime_keys)) != len(runtime_keys):
        raise ValueError("portfolio runtime keys must be unique")
    if allocations is None:
        return (1.0,) * len(runtime_keys)
    if len(allocations) != len(runtime_keys):
        raise ValueError("portfolio allocations must match runtime keys")
    if any(not isfinite(value) or not 0.0 < value <= 1.0 for value in allocations):
        raise ValueError("portfolio allocations must be finite and in (0, 1]")
    return allocations


def calculate_allocated_performance_metrics(
    trades: Iterable[TradeSnapshot],
    allocations_by_symbol: dict[str, float],
) -> TradePerformanceMetrics:
    """Compute cash PnL and drawdown at actual sleeve allocations.

    Trade count and PnL coverage remain event counts, not fractional weights.
    """
    return calculate_performance_metrics(
        replace(trade, pnl=trade.pnl * allocations_by_symbol[trade.symbol])
        for trade in trades
        if trade.symbol in allocations_by_symbol
    )


def empty_performance_payload() -> dict[str, object]:
    return {
        "available": False,
        "trade_count": 0,
        "pnl_observations": 0,
        "pnl_coverage": None,
        "realized_pnl": None,
        "average_pnl": None,
        "gross_profit": None,
        "gross_loss": None,
        "profit_factor": None,
        "profit_factor_infinite": False,
        "max_drawdown": None,
    }


def performance_payload(metrics: TradePerformanceMetrics) -> dict[str, object]:
    trade_count = int(metrics.trade_count)
    observations = int(metrics.pnl_observations)
    available = observations > 0
    profit_factor = metrics.profit_factor
    profit_factor_infinite = (
        profit_factor is not None and not isfinite(float(profit_factor))
    )
    return {
        "available": available,
        "trade_count": trade_count,
        "pnl_observations": observations,
        "pnl_coverage": observations / trade_count if trade_count > 0 else None,
        "realized_pnl": float(metrics.realized_pnl) if available else None,
        "average_pnl": float(metrics.average_pnl) if available else None,
        "gross_profit": float(metrics.gross_profit) if available else None,
        "gross_loss": float(metrics.gross_loss) if available else None,
        "profit_factor": (
            None
            if not available or profit_factor is None or profit_factor_infinite
            else float(profit_factor)
        ),
        "profit_factor_infinite": profit_factor_infinite if available else False,
        "max_drawdown": float(metrics.max_drawdown) if available else None,
    }

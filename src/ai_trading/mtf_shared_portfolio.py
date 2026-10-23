from __future__ import annotations

from dataclasses import dataclass
from math import isclose, isfinite

import pandas as pd

from .mtf_parameter_benchmark import MarketBenchmarkResult, MTFResearchTrade


@dataclass
class _Position:
    units: float
    entry_price: float
    entry_cost: float


@dataclass(frozen=True)
class SharedMTFPortfolioReport:
    starting_cash: float
    final_equity: float
    net_return: float
    max_drawdown: float
    max_concurrent_positions: int
    peak_gross_exposure_fraction: float
    entry_gross_limit: float
    per_market_target_fraction: float
    accepted_trades: int
    rejected_entries: int
    total_costs: float
    realized_net_pnl: float
    equity_by_timestamp: dict[str, float]
    fills: tuple[dict[str, object], ...]


def simulate_shared_mtf_portfolio(
    markets: dict[str, pd.DataFrame],
    results: tuple[MarketBenchmarkResult, ...],
    *,
    starting_cash: float = 100_000.0,
    per_market_fraction: float = 0.10,
    max_gross_fraction: float = 0.30,
) -> SharedMTFPortfolioReport:
    """Replay already predicted OOS trades with one shared, unlevered risk budget.

    Every trade is an output of the existing research benchmark, *not* a
    broker fill. At a timestamp, positions enter at that bar's open using
    only prices previously closed on other markets. Existing and new
    holdings are marked at completed closes, then scheduled exits settle.
    Exit proceeds cannot fund same-timestamp opening orders. Weekend and
    session gaps carry the last observed close, not a future price.

    Each market has at most one open position. Both long and short notional
    consume the same gross exposure budget. Borrow, margin, asset currency
    conversion and funding are NOT modeled; prices are normalized proxies.
    """
    if (
        not isfinite(starting_cash)
        or starting_cash <= 0
        or not isfinite(per_market_fraction)
        or not 0 < per_market_fraction <= 1
        or not isfinite(max_gross_fraction)
        or not 0 < max_gross_fraction <= 1
    ):
        raise ValueError("shared research equity and gross exposure must be positive and finite")
    if len(markets) < 2 or len(results) != len(markets):
        raise ValueError("shared research requires one result for each of two or more markets")
    rows = {row.symbol: row for row in results}
    if len(rows) != len(results) or set(rows) != set(markets):
        raise ValueError("each market must have exactly one matching research result")

    bars: dict[str, pd.DataFrame] = {}
    entries: dict[pd.Timestamp, list[tuple[str, MTFResearchTrade]]] = {}
    exits: dict[pd.Timestamp, list[tuple[str, MTFResearchTrade]]] = {}
    for symbol in sorted(markets):
        market = markets[symbol]
        if (
            not isinstance(market.index, pd.DatetimeIndex)
            or market.index.hasnans
            or market.index.has_duplicates
            or not market.index.is_monotonic_increasing
            or not {"Open", "Close"}.issubset(market.columns)
        ):
            raise ValueError(f"{symbol}: invalid dated OHLC market history")
        frame = market.loc[:, ["Open", "Close"]].astype(float).copy()
        if frame.empty or not frame.map(lambda price: isfinite(price) and price > 0).all().all():
            raise ValueError(f"{symbol}: OHLC prices must be finite and positive")
        frame.index = pd.to_datetime(frame.index, utc=True)
        bars[symbol] = frame

        if len(rows[symbol].paper_trades) != rows[symbol].economic_trades:
            raise ValueError(f"{symbol}: incomplete time-aligned research fills")
        last_exit: pd.Timestamp | None = None
        for trade in sorted(
            rows[symbol].paper_trades,
            key=lambda item: pd.Timestamp(item.entry_time),
        ):
            start = pd.Timestamp(trade.entry_time)
            end = pd.Timestamp(trade.exit_time)
            start = start.tz_localize("UTC") if start.tzinfo is None else start.tz_convert("UTC")
            end = end.tz_localize("UTC") if end.tzinfo is None else end.tz_convert("UTC")
            if (
                trade.side not in (-1, 1)
                or start not in frame.index
                or end not in frame.index
                or start >= end
                or (last_exit is not None and start <= last_exit)
                or not isclose(float(trade.entry_price), float(frame.at[start, "Open"]), rel_tol=1e-10)
                or not isclose(float(trade.exit_price), float(frame.at[end, "Close"]), rel_tol=1e-10)
            ):
                raise ValueError(f"{symbol}: invalid, overlapping or mismatched research trade")
            last_exit = end
            entries.setdefault(start, []).append((symbol, trade))
            exits.setdefault(end, []).append((symbol, trade))
        if (
            not isfinite(rows[symbol].transaction_cost_bps)
            or not isfinite(rows[symbol].slippage_bps)
            or min(rows[symbol].transaction_cost_bps, rows[symbol].slippage_bps) < 0
        ):
            raise ValueError(f"{symbol}: invalid execution costs")

    entry_events = {
        time: sorted(events, key=lambda x: x[0]) for time, events in entries.items()
    }
    exit_events = {
        time: sorted(events, key=lambda x: x[0]) for time, events in exits.items()
    }
    union = sorted(set().union(*(frame.index for frame in bars.values())))
    cash = float(starting_cash)
    marked_prices: dict[str, float] = {}
    positions: dict[str, _Position] = {}
    equity_curve: dict[str, float] = {}
    fills: list[dict[str, object]] = []
    total_costs = 0.0
    realized_net_pnl = 0.0
    accepted = 0
    rejected = 0
    peak_equity = float(starting_cash)
    worst_drawdown = 0.0
    max_concurrent = 0
    peak_exposure = 0.0

    def mark() -> float:
        return cash + sum(pos.units * marked_prices[sym] for sym, pos in positions.items())

    def observe() -> None:
        nonlocal peak_equity, worst_drawdown, peak_exposure, max_concurrent
        equity = mark()
        if not isfinite(equity) or equity <= 0:
            raise ValueError("shared research equity exhausted or invalid")
        peak_equity = max(peak_equity, equity)
        worst_drawdown = max(worst_drawdown, 1 - equity / peak_equity)
        gross = sum(abs(pos.units * marked_prices[sym]) for sym, pos in positions.items())
        peak_exposure = max(peak_exposure, gross / equity)
        max_concurrent = max(max_concurrent, len(positions))

    for timestamp in union:
        # Open orders execute before any close or same-bar exit. All symbols
        # share one account. Stable sorted ordering is an explicit assumption.
        for symbol, trade in entry_events.get(timestamp, ()):
            if symbol in positions:
                raise ValueError(f"{symbol}: overlapping active research positions")
            price = float(bars[symbol].at[timestamp, "Open"])
            equity_before = mark()
            current_gross = sum(
                abs(pos.units * marked_prices[sym]) for sym, pos in positions.items()
            )
            rate = (rows[symbol].transaction_cost_bps + rows[symbol].slippage_bps) / 10_000.0
            capacity = max(0.0, max_gross_fraction * equity_before - current_gross)
            # The entry fee reduces equity and therefore shrinks the
            # post-fill gross budget. Do not spend that difference twice.
            allowable = capacity / (1.0 + max_gross_fraction * rate)
            notional = min(per_market_fraction * equity_before, allowable)
            if not isfinite(notional) or notional <= 1e-8:
                rejected += 1
                continue
            units = trade.side * notional / price
            fee = notional * rate
            cash -= units * price + fee
            total_costs += fee
            positions[symbol] = _Position(units=units, entry_price=price, entry_cost=fee)
            marked_prices[symbol] = price
            accepted += 1
            fills.append({
                "timestamp": timestamp.isoformat(), "symbol": symbol, "action": "entry",
                "units": units, "price": price, "cost": fee,
            })
            observe()

        # Only completed close prices are made available, no forward-looking
        # marks for a market that has not printed a new bar.
        for symbol, frame in bars.items():
            if timestamp in frame.index:
                marked_prices[symbol] = float(frame.at[timestamp, "Close"])
        observe()

        for symbol, trade in exit_events.get(timestamp, ()):
            if symbol not in positions:
                # A trade rejected at entry must not create a fictitious exit.
                continue
            position = positions.pop(symbol)
            price = float(bars[symbol].at[timestamp, "Close"])
            rate = (rows[symbol].transaction_cost_bps + rows[symbol].slippage_bps) / 10_000.0
            fee = abs(position.units) * price * rate
            cash += position.units * price - fee
            total_costs += fee
            pnl = position.units * (price - position.entry_price) - position.entry_cost - fee
            realized_net_pnl += pnl
            fills.append({
                "timestamp": timestamp.isoformat(), "symbol": symbol, "action": "exit",
                "units": -position.units, "price": price, "cost": fee, "realized_pnl": pnl,
            })
            observe()
        equity_curve[timestamp.isoformat()] = mark()

    if positions or accepted * 2 != len(fills):
        raise ValueError("shared research has unfinished or unbalanced positions")
    final_equity = mark()
    if not isclose(final_equity - starting_cash, realized_net_pnl, rel_tol=1e-7, abs_tol=1e-6):
        raise ValueError("shared account cash and realized PnL do not reconcile")
    return SharedMTFPortfolioReport(
        starting_cash=starting_cash,
        final_equity=final_equity,
        net_return=final_equity / starting_cash - 1.0,
        max_drawdown=worst_drawdown,
        max_concurrent_positions=max_concurrent,
        peak_gross_exposure_fraction=peak_exposure,
        entry_gross_limit=max_gross_fraction,
        per_market_target_fraction=per_market_fraction,
        accepted_trades=accepted,
        rejected_entries=rejected,
        total_costs=total_costs,
        realized_net_pnl=realized_net_pnl,
        equity_by_timestamp=equity_curve,
        fills=tuple(fills),
    )

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite

from .config import RiskConfig
from .paper_execution import calculate_rebalance_fill


@dataclass
class BrokerState:
    cash: float
    units: float = 0.0
    last_price: float = 0.0
    peak_equity: float = 0.0
    day_start_equity: float = 0.0

    @property
    def equity(self) -> float:
        return self.cash + self.units * self.last_price


class PaperBroker:
    def __init__(self, config: RiskConfig) -> None:
        self.config = config
        self.state = BrokerState(
            cash=config.starting_cash,
            peak_equity=config.starting_cash,
            day_start_equity=config.starting_cash,
        )

    def mark(self, price: float) -> None:
        price = float(price)
        if not isfinite(price) or price <= 0:
            raise ValueError("price must be finite and positive")
        self.state.last_price = price
        equity = self.state.equity
        self.state.peak_equity = max(self.state.peak_equity, equity)

    def reset_day_start(self) -> None:
        self.state.day_start_equity = self.state.equity

    def rebalance(self, side: int, target_notional: float, price: float) -> None:
        if side not in {-1, 0, 1}:
            raise ValueError("side must be -1, 0, or 1")
        target_notional = float(target_notional)
        if not isfinite(target_notional) or target_notional < 0:
            raise ValueError("target_notional must be finite and non-negative")
        self.mark(price)
        signed_target_notional = 0.0 if side == 0 else side * target_notional
        fill = calculate_rebalance_fill(
            current_units=self.state.units,
            target_notional=signed_target_notional,
            price=price,
            transaction_cost_bps=self.config.transaction_cost_bps,
            slippage_bps=self.config.slippage_bps,
        )

        self.state.cash -= fill.delta_units * price
        self.state.cash -= fill.costs
        self.state.units = fill.desired_units
        self.mark(price)

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite


@dataclass(frozen=True)
class RebalanceFill:
    desired_units: float
    delta_units: float
    gross_turnover: float
    costs: float
    realized_gross_pnl: float | None
    realized_net_pnl: float | None
    next_average_entry_price: float


def calculate_rebalance_fill(
    *,
    current_units: float,
    current_average_entry_price: float = 0.0,
    target_notional: float,
    price: float,
    transaction_cost_bps: float,
    slippage_bps: float,
) -> RebalanceFill:
    values = {
        "current_units": float(current_units),
        "current_average_entry_price": float(current_average_entry_price),
        "target_notional": float(target_notional),
        "price": float(price),
        "transaction_cost_bps": float(transaction_cost_bps),
        "slippage_bps": float(slippage_bps),
    }
    for name, value in values.items():
        if not isfinite(value):
            raise ValueError(f"{name} must be finite")

    if values["price"] <= 0:
        raise ValueError("price must be positive")
    if values["current_average_entry_price"] < 0:
        raise ValueError("current_average_entry_price must be non-negative")
    if values["transaction_cost_bps"] < 0 or values["slippage_bps"] < 0:
        raise ValueError("execution costs must be non-negative")

    desired_units = values["target_notional"] / values["price"]
    delta_units = desired_units - values["current_units"]
    gross_turnover = abs(delta_units) * values["price"]
    costs = gross_turnover * (
        values["transaction_cost_bps"] + values["slippage_bps"]
    ) / 10_000.0

    current = values["current_units"]
    average = values["current_average_entry_price"]
    epsilon = 1e-12
    closing_units = 0.0
    if abs(current) > epsilon and delta_units * current < 0:
        closing_units = min(abs(delta_units), abs(current))

    if closing_units > epsilon:
        if average > 0:
            direction = 1.0 if current > 0 else -1.0
            realized_gross_pnl: float | None = (
                closing_units * (values["price"] - average) * direction
            )
        else:
            realized_gross_pnl = None
    else:
        realized_gross_pnl = 0.0

    if abs(desired_units) <= epsilon:
        next_average_entry_price = 0.0
    elif abs(current) <= epsilon or current * desired_units < 0:
        next_average_entry_price = values["price"]
    elif abs(desired_units) > abs(current) + epsilon:
        added_units = abs(desired_units) - abs(current)
        next_average_entry_price = (
            (
                abs(current) * average
                + added_units * values["price"]
            )
            / abs(desired_units)
            if average > 0
            else 0.0
        )
    else:
        next_average_entry_price = average

    realized_net_pnl = (
        None if realized_gross_pnl is None else realized_gross_pnl - costs
    )

    return RebalanceFill(
        desired_units=desired_units,
        delta_units=delta_units,
        gross_turnover=gross_turnover,
        costs=costs,
        realized_gross_pnl=realized_gross_pnl,
        realized_net_pnl=realized_net_pnl,
        next_average_entry_price=next_average_entry_price,
    )

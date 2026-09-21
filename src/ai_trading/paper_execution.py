from __future__ import annotations

from dataclasses import dataclass
from math import isfinite


@dataclass(frozen=True)
class RebalanceFill:
    desired_units: float
    delta_units: float
    gross_turnover: float
    costs: float


def calculate_rebalance_fill(
    *,
    current_units: float,
    target_notional: float,
    price: float,
    transaction_cost_bps: float,
    slippage_bps: float,
) -> RebalanceFill:
    values = {
        "current_units": float(current_units),
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
    if values["transaction_cost_bps"] < 0 or values["slippage_bps"] < 0:
        raise ValueError("execution costs must be non-negative")

    desired_units = values["target_notional"] / values["price"]
    delta_units = desired_units - values["current_units"]
    gross_turnover = abs(delta_units) * values["price"]
    costs = gross_turnover * (
        values["transaction_cost_bps"] + values["slippage_bps"]
    ) / 10_000.0

    return RebalanceFill(
        desired_units=desired_units,
        delta_units=delta_units,
        gross_turnover=gross_turnover,
        costs=costs,
    )

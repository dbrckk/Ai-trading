from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class AssetPnL:
    symbol: str
    pnl: float
    return_contribution: float


def attribute_pnl(
    previous_prices: dict[str, float],
    current_prices: dict[str, float],
    units: dict[str, float],
    starting_equity: float,
) -> dict[str, AssetPnL]:
    if starting_equity <= 0:
        raise ValueError("starting_equity must be positive")

    out: dict[str, AssetPnL] = {}
    for symbol, qty in units.items():
        if symbol not in previous_prices or symbol not in current_prices:
            continue
        pnl = float(qty) * (float(current_prices[symbol]) - float(previous_prices[symbol]))
        out[symbol] = AssetPnL(
            symbol=symbol,
            pnl=pnl,
            return_contribution=pnl / starting_equity,
        )
    return out


def attribution_frame(attribution: dict[str, AssetPnL]) -> pd.DataFrame:
    if not attribution:
        return pd.DataFrame(columns=["pnl", "return_contribution"])
    return pd.DataFrame(
        {
            symbol: {
                "pnl": item.pnl,
                "return_contribution": item.return_contribution,
            }
            for symbol, item in attribution.items()
        }
    ).T

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AlphaContribution:
    symbol: str
    model: str
    regime: str
    pnl: float
    return_contribution: float


def build_alpha_contribution(
    *,
    symbol: str,
    model: str,
    regime: str,
    pnl: float,
    portfolio_equity: float,
) -> AlphaContribution:
    if portfolio_equity <= 0:
        raise ValueError("portfolio_equity must be positive")
    return AlphaContribution(
        symbol=symbol,
        model=model,
        regime=regime,
        pnl=float(pnl),
        return_contribution=float(pnl / portfolio_equity),
    )

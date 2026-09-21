from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from .performance import compute_metrics


@dataclass(frozen=True)
class MarginalAlphaReport:
    marginal_return: float
    marginal_sharpe: float
    marginal_drawdown: float
    correlation_to_portfolio: float
    improves_portfolio: bool


def evaluate_marginal_alpha(
    portfolio_returns: pd.Series,
    candidate_returns: pd.Series,
    *,
    blend_weight: float = 0.20,
    max_correlation: float = 0.85,
) -> MarginalAlphaReport:
    frame = pd.concat(
        [
            portfolio_returns.rename("portfolio"),
            candidate_returns.rename("candidate"),
        ],
        axis=1,
        sort=False,
    ).dropna()
    if len(frame) < 20:
        raise ValueError("Need at least 20 aligned observations")

    base_equity = (1.0 + frame["portfolio"]).cumprod() * 100_000.0
    blended_returns = (
        (1.0 - blend_weight) * frame["portfolio"]
        + blend_weight * frame["candidate"]
    )
    blended_equity = (1.0 + blended_returns).cumprod() * 100_000.0

    base = compute_metrics(base_equity)
    blended = compute_metrics(blended_equity)
    corr = float(frame["portfolio"].corr(frame["candidate"]))
    if pd.isna(corr):
        corr = 0.0

    marginal_return = blended.total_return - base.total_return
    marginal_sharpe = blended.sharpe - base.sharpe
    marginal_drawdown = blended.max_drawdown - base.max_drawdown

    improves = (
        marginal_return > 0.0
        and marginal_sharpe >= 0.0
        and marginal_drawdown <= 0.02
        and abs(corr) <= max_correlation
    )

    return MarginalAlphaReport(
        marginal_return=float(marginal_return),
        marginal_sharpe=float(marginal_sharpe),
        marginal_drawdown=float(marginal_drawdown),
        correlation_to_portfolio=float(corr),
        improves_portfolio=improves,
    )

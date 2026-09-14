from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class GlobalAllocatorConfig:
    cvar_alpha: float = 0.95
    max_cvar: float = 0.03
    max_asset_weight: float = 0.40
    max_expert_weight: float = 0.25
    max_turnover: float = 0.30
    target_gross_exposure: float = 1.0
    cost_penalty: float = 1.0
    turnover_penalty: float = 0.25


@dataclass(frozen=True)
class GlobalAllocationReport:
    weights: pd.Series
    cvar: float
    expected_return: float
    turnover: float
    estimated_cost: float
    approved: bool
    reasons: tuple[str, ...]


def expected_shortfall(
    returns: pd.Series,
    *,
    alpha: float = 0.95,
) -> float:
    clean = returns.astype(float).dropna()
    if clean.empty:
        return 0.0
    cutoff = float(clean.quantile(1.0 - alpha))
    tail = clean[clean <= cutoff]
    if tail.empty:
        return 0.0
    return float(-tail.mean())


def _normalize_capped(
    scores: pd.Series,
    *,
    cap: float,
    target: float,
) -> pd.Series:
    positive = scores.clip(lower=0.0).astype(float)
    if float(positive.sum()) <= 0:
        return pd.Series(0.0, index=positive.index, dtype=float)

    result = pd.Series(0.0, index=positive.index, dtype=float)
    free = list(positive.index)
    remaining = float(target)

    while free and remaining > 1e-12:
        base = positive.loc[free]
        total = float(base.sum())
        proposal = (
            pd.Series(remaining / len(free), index=free, dtype=float)
            if total <= 0
            else base / total * remaining
        )
        over = proposal[proposal > cap + 1e-12]
        if over.empty:
            result.loc[free] = proposal
            break
        for item in over.index:
            result.loc[item] = cap
            remaining -= cap
            free.remove(item)

    return result


def allocate_global_capital(
    opportunity_returns: pd.DataFrame,
    expected_alpha: pd.Series,
    quality: pd.Series,
    current_weights: pd.Series | None = None,
    *,
    transaction_cost_bps: float = 3.0,
    config: GlobalAllocatorConfig | None = None,
) -> GlobalAllocationReport:
    config = config or GlobalAllocatorConfig()
    columns = opportunity_returns.columns
    alpha = expected_alpha.reindex(columns).fillna(0.0).astype(float)
    q = quality.reindex(columns).fillna(0.0).clip(lower=0.0).astype(float)

    vol = opportunity_returns.astype(float).std(ddof=1).replace(0.0, np.nan)
    raw_score = (alpha.clip(lower=0.0) * q / vol).replace([np.inf, -np.inf], np.nan).fillna(0.0)
    weights = _normalize_capped(
        raw_score,
        cap=config.max_expert_weight,
        target=config.target_gross_exposure,
    )

    # Enforce asset-level concentration if columns use "asset|expert|regime".
    asset_totals: dict[str, float] = {}
    for key, value in weights.items():
        asset = str(key).split("|", 1)[0]
        asset_totals[asset] = asset_totals.get(asset, 0.0) + float(value)

    for asset, total in asset_totals.items():
        if total <= config.max_asset_weight + 1e-12:
            continue
        scale = config.max_asset_weight / total
        for key in weights.index:
            if str(key).split("|", 1)[0] == asset:
                weights.loc[key] *= scale

    # Do not renormalize upward after asset caps: doing so could violate
    # concentration constraints. A constrained portfolio may intentionally
    # run below target gross exposure.
    gross = float(weights.sum())
    if gross > config.target_gross_exposure + 1e-12:
        weights *= config.target_gross_exposure / gross

    current = (
        current_weights.reindex(columns).fillna(0.0).astype(float)
        if current_weights is not None
        else pd.Series(0.0, index=columns, dtype=float)
    )
    turnover = float((weights - current).abs().sum())
    estimated_cost = turnover * transaction_cost_bps / 10_000.0

    portfolio_returns = opportunity_returns.fillna(0.0).mul(weights, axis=1).sum(axis=1)
    cvar = expected_shortfall(portfolio_returns, alpha=config.cvar_alpha)
    expected_return = float(portfolio_returns.mean())

    reasons: list[str] = []
    if cvar > config.max_cvar:
        reasons.append("CVaR limit exceeded")
    if turnover > config.max_turnover:
        reasons.append("turnover limit exceeded")
    if estimated_cost * config.cost_penalty > max(0.0, expected_return):
        reasons.append("cost exceeds expected return")

    return GlobalAllocationReport(
        weights=weights,
        cvar=float(cvar),
        expected_return=expected_return,
        turnover=turnover,
        estimated_cost=float(estimated_cost),
        approved=not reasons,
        reasons=tuple(reasons),
    )

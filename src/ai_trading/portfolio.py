from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class AllocationConfig:
    max_asset_weight: float = 0.35
    min_asset_weight: float = 0.0
    target_gross_exposure: float = 1.0
    correlation_penalty: float = 0.50


def _cap_and_normalize(
    weights: pd.Series,
    *,
    max_weight: float,
    target_sum: float,
) -> pd.Series:
    if max_weight <= 0 or target_sum <= 0:
        raise ValueError("max_weight and target_sum must be positive")
    if len(weights) * max_weight + 1e-12 < target_sum:
        raise ValueError("max_asset_weight is infeasible for the number of assets")

    base = weights.clip(lower=0.0).astype(float)
    if float(base.sum()) <= 0:
        base[:] = 1.0

    result = pd.Series(0.0, index=base.index, dtype=float)
    free = list(base.index)
    remaining = float(target_sum)

    while free:
        free_base = base.loc[free]
        total = float(free_base.sum())
        if total <= 0:
            proposal = pd.Series(remaining / len(free), index=free, dtype=float)
        else:
            proposal = free_base / total * remaining

        over = proposal[proposal > max_weight + 1e-12]
        if over.empty:
            result.loc[free] = proposal
            break

        for asset in over.index:
            result.loc[asset] = max_weight
            remaining -= max_weight
            free.remove(asset)

        if remaining <= 1e-12:
            break

    return result


def inverse_volatility_weights(
    returns: pd.DataFrame,
    config: AllocationConfig | None = None,
) -> pd.Series:
    config = config or AllocationConfig()
    clean = returns.astype(float).dropna(how="all")
    if clean.empty or clean.shape[1] == 0:
        raise ValueError("returns must contain at least one asset")

    vol = clean.std(ddof=1).replace(0.0, np.nan)
    inv = (1.0 / vol).replace([np.inf, -np.inf], np.nan).fillna(0.0)
    if float(inv.sum()) <= 0:
        raw = pd.Series(1.0 / len(inv), index=inv.index, dtype=float)
    else:
        raw = inv / inv.sum()

    corr = clean.corr().fillna(0.0).abs()
    penalties = pd.Series(1.0, index=raw.index, dtype=float)
    for asset in raw.index:
        peers = corr.loc[asset].drop(labels=[asset], errors="ignore")
        avg_corr = float(peers.mean()) if len(peers) else 0.0
        penalties.loc[asset] = max(0.0, 1.0 - config.correlation_penalty * avg_corr)

    adjusted = raw * penalties
    if float(adjusted.sum()) <= 0:
        adjusted = raw.copy()

    adjusted = adjusted.clip(lower=config.min_asset_weight)
    return _cap_and_normalize(
        adjusted,
        max_weight=config.max_asset_weight,
        target_sum=config.target_gross_exposure,
    )


def target_notionals(
    equity: float,
    weights: pd.Series,
) -> pd.Series:
    if equity <= 0:
        raise ValueError("equity must be positive")
    return weights.astype(float) * float(equity)

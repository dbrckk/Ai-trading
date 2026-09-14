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
    adjusted = adjusted / adjusted.sum()

    capped = adjusted.clip(
        lower=config.min_asset_weight,
        upper=config.max_asset_weight,
    )
    if float(capped.sum()) <= 0:
        raise ValueError("allocation collapsed to zero")

    normalized = capped / capped.sum()
    return normalized * config.target_gross_exposure


def target_notionals(
    equity: float,
    weights: pd.Series,
) -> pd.Series:
    if equity <= 0:
        raise ValueError("equity must be positive")
    return weights.astype(float) * float(equity)

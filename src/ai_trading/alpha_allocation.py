from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class AlphaAllocationConfig:
    max_asset_weight: float = 0.35
    target_gross_exposure: float = 1.0
    min_signal_quality: float = 0.05

    def __post_init__(self) -> None:
        if not 0.0 < self.max_asset_weight <= 1.0:
            raise ValueError("max_asset_weight must be in (0, 1]")
        if self.target_gross_exposure <= 0:
            raise ValueError("target_gross_exposure must be positive")
        if not 0.0 <= self.min_signal_quality <= 1.0:
            raise ValueError("min_signal_quality must be in [0, 1]")


def alpha_risk_weights(
    expected_alpha: pd.Series,
    annualized_volatility: pd.Series,
    quality: pd.Series,
    config: AlphaAllocationConfig | None = None,
) -> pd.Series:
    config = config or AlphaAllocationConfig()

    alpha = expected_alpha.astype(float)
    vol = annualized_volatility.astype(float).replace(0.0, np.nan)
    q = quality.reindex(alpha.index).fillna(0.0).astype(float)

    score = alpha.abs() * q.clip(lower=config.min_signal_quality) / vol
    score = score.replace([np.inf, -np.inf], np.nan).fillna(0.0)

    if float(score.sum()) <= 0:
        return pd.Series(0.0, index=alpha.index, dtype=float)

    raw = score / score.sum() * config.target_gross_exposure
    raw = raw.clip(upper=config.max_asset_weight)

    # Iteratively redistribute residual without breaking caps.
    result = raw.copy()
    for _ in range(20):
        residual = config.target_gross_exposure - float(result.sum())
        if residual <= 1e-12:
            break
        free = result[result < config.max_asset_weight - 1e-12]
        if free.empty:
            break
        increments = free / free.sum() * residual if float(free.sum()) > 0 else residual / len(free)
        for asset in free.index:
            add = float(increments.loc[asset] if hasattr(increments, "loc") else increments)
            result.loc[asset] = min(config.max_asset_weight, result.loc[asset] + add)

    signs = np.sign(alpha)
    return result * signs

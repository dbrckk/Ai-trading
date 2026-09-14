from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class BootstrapReport:
    median_return: float
    p05_return: float
    p95_return: float
    probability_positive: float
    probability_loss_gt_10pct: float


def block_bootstrap_returns(
    equity: pd.Series,
    *,
    simulations: int = 1000,
    block_size: int = 5,
    random_state: int = 42,
) -> BootstrapReport:
    clean = equity.astype(float).dropna()
    returns = clean.pct_change().dropna().to_numpy(dtype=float)
    if len(returns) < max(10, block_size):
        raise ValueError("Need more return observations for bootstrap")
    if simulations < 100:
        raise ValueError("simulations must be at least 100")
    if block_size < 1:
        raise ValueError("block_size must be positive")

    rng = np.random.default_rng(random_state)
    n = len(returns)
    possible = max(1, n - block_size + 1)
    outcomes = np.empty(simulations, dtype=float)

    for i in range(simulations):
        sampled: list[float] = []
        while len(sampled) < n:
            start = int(rng.integers(0, possible))
            sampled.extend(returns[start : start + block_size].tolist())
        path = np.asarray(sampled[:n], dtype=float)
        outcomes[i] = float(np.prod(1.0 + path) - 1.0)

    return BootstrapReport(
        median_return=float(np.median(outcomes)),
        p05_return=float(np.quantile(outcomes, 0.05)),
        p95_return=float(np.quantile(outcomes, 0.95)),
        probability_positive=float(np.mean(outcomes > 0.0)),
        probability_loss_gt_10pct=float(np.mean(outcomes < -0.10)),
    )

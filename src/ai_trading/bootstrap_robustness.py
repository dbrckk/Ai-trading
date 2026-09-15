from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class BootstrapConfig:
    simulations: int = 2000
    confidence: float = 0.95
    seed: int = 42
    block_size: int = 5


@dataclass(frozen=True)
class BootstrapReport:
    simulations: int
    probability_positive: float
    probability_loss: float
    median_return: float
    lower_return: float
    upper_return: float
    median_max_drawdown: float
    upper_max_drawdown: float


def bootstrap_equity_curve(
    equity_curve: pd.Series,
    config: BootstrapConfig | None = None,
) -> BootstrapReport:
    config = config or BootstrapConfig()
    if config.simulations < 100:
        raise ValueError("simulations must be at least 100")
    if not 0.5 < config.confidence < 1.0:
        raise ValueError("confidence must be between 0.5 and 1.0")
    if config.block_size < 1:
        raise ValueError("block_size must be positive")

    returns = (
        equity_curve.astype(float)
        .pct_change()
        .replace([np.inf, -np.inf], np.nan)
        .dropna()
        .to_numpy()
    )
    if len(returns) < 2:
        raise ValueError("equity curve must contain at least three valid observations")

    rng = np.random.default_rng(config.seed)
    simulated_returns = np.empty(config.simulations)
    simulated_drawdowns = np.empty(config.simulations)

    for simulation in range(config.simulations):
        sample = _block_bootstrap(
            returns,
            rng=rng,
            block_size=min(config.block_size, len(returns)),
        )
        wealth = np.cumprod(1.0 + sample)
        simulated_returns[simulation] = wealth[-1] - 1.0
        peak = np.maximum.accumulate(wealth)
        drawdown = 1.0 - wealth / peak
        simulated_drawdowns[simulation] = float(np.max(drawdown))

    alpha = (1.0 - config.confidence) / 2.0
    return BootstrapReport(
        simulations=config.simulations,
        probability_positive=float(np.mean(simulated_returns > 0.0)),
        probability_loss=float(np.mean(simulated_returns < 0.0)),
        median_return=float(np.median(simulated_returns)),
        lower_return=float(np.quantile(simulated_returns, alpha)),
        upper_return=float(np.quantile(simulated_returns, 1.0 - alpha)),
        median_max_drawdown=float(np.median(simulated_drawdowns)),
        upper_max_drawdown=float(
            np.quantile(simulated_drawdowns, config.confidence)
        ),
    )


def _block_bootstrap(
    returns: np.ndarray,
    *,
    rng: np.random.Generator,
    block_size: int,
) -> np.ndarray:
    output: list[float] = []
    max_start = len(returns) - block_size
    while len(output) < len(returns):
        start = int(rng.integers(0, max_start + 1))
        output.extend(returns[start : start + block_size])
    return np.asarray(output[: len(returns)], dtype=float)

from __future__ import annotations

from dataclasses import asdict, dataclass

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class PerformanceMetrics:
    total_return: float
    annualized_return: float
    annualized_volatility: float
    sharpe: float
    sortino: float
    max_drawdown: float
    calmar: float

    def as_dict(self) -> dict[str, float]:
        return asdict(self)


def _safe_ratio(numerator: float, denominator: float) -> float:
    if not np.isfinite(denominator) or abs(denominator) < 1e-12:
        return 0.0
    return float(numerator / denominator)


def infer_periods_per_year(index: pd.Index) -> float:
    timestamps = pd.to_datetime(index, utc=True, errors="coerce")
    timestamps = timestamps[~timestamps.isna()]
    if len(timestamps) < 2:
        raise ValueError("Need at least two valid timestamps")
    elapsed_seconds = float((timestamps[-1] - timestamps[0]).total_seconds())
    if elapsed_seconds <= 0:
        raise ValueError("Timestamps must span positive time")
    elapsed_years = elapsed_seconds / (365.25 * 24 * 60 * 60)
    return float((len(timestamps) - 1) / elapsed_years)


def compute_metrics(equity: pd.Series, periods_per_year: float = 252.0) -> PerformanceMetrics:
    clean = equity.astype(float).dropna()
    if len(clean) < 2:
        raise ValueError("Need at least two equity observations")

    returns = clean.pct_change().dropna()
    total_return = float(clean.iloc[-1] / clean.iloc[0] - 1.0)

    if periods_per_year <= 0 or not np.isfinite(periods_per_year):
        raise ValueError("periods_per_year must be positive and finite")
    years = max((len(returns) / periods_per_year), 1.0 / periods_per_year)
    if clean.iloc[0] > 0 and clean.iloc[-1] > 0:
        annualized_return = float((clean.iloc[-1] / clean.iloc[0]) ** (1.0 / years) - 1.0)
    else:
        annualized_return = 0.0

    volatility = float(returns.std(ddof=1) * np.sqrt(periods_per_year)) if len(returns) > 1 else 0.0
    mean_ann = float(returns.mean() * periods_per_year) if len(returns) else 0.0
    sharpe = _safe_ratio(mean_ann, volatility)

    downside = returns[returns < 0]
    downside_dev = (
        float(downside.std(ddof=1) * np.sqrt(periods_per_year))
        if len(downside) > 1
        else 0.0
    )
    sortino = _safe_ratio(mean_ann, downside_dev)

    running_max = clean.cummax()
    drawdowns = 1.0 - clean / running_max
    max_drawdown = float(drawdowns.max())
    calmar = _safe_ratio(annualized_return, max_drawdown)

    return PerformanceMetrics(
        total_return=total_return,
        annualized_return=annualized_return,
        annualized_volatility=volatility,
        sharpe=sharpe,
        sortino=sortino,
        max_drawdown=max_drawdown,
        calmar=calmar,
    )


def buy_and_hold_equity(
    prices: pd.Series,
    starting_equity: float,
) -> pd.Series:
    clean = prices.astype(float).dropna()
    if clean.empty or clean.iloc[0] <= 0:
        raise ValueError("Need positive benchmark prices")
    return starting_equity * clean / clean.iloc[0]

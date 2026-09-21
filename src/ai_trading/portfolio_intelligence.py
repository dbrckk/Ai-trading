from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class PortfolioIntelligenceConfig:
    target_annual_volatility: float = 0.12
    min_leverage: float = 0.10
    max_leverage: float = 1.00
    drawdown_soft_limit: float = 0.05
    drawdown_hard_limit: float = 0.12
    stress_vol_multiplier: float = 1.75
    confidence_floor: float = 0.50
    confidence_power: float = 2.0
    correlation_soft_limit: float = 0.70
    correlation_hard_limit: float = 0.90

    def __post_init__(self) -> None:
        if self.target_annual_volatility <= 0:
            raise ValueError("target_annual_volatility must be positive")
        if self.min_leverage <= 0 or self.max_leverage < self.min_leverage:
            raise ValueError("leverage bounds must satisfy 0 < min_leverage <= max_leverage")
        if not 0.0 <= self.drawdown_soft_limit < self.drawdown_hard_limit <= 1.0:
            raise ValueError("drawdown limits must satisfy 0 <= soft < hard <= 1")
        if self.stress_vol_multiplier <= 0:
            raise ValueError("stress_vol_multiplier must be positive")
        if not 0.0 <= self.confidence_floor < 1.0:
            raise ValueError("confidence_floor must be in [0, 1)")
        if self.confidence_power <= 0:
            raise ValueError("confidence_power must be positive")
        if not 0.0 <= self.correlation_soft_limit < self.correlation_hard_limit <= 1.0:
            raise ValueError("correlation limits must satisfy 0 <= soft < hard <= 1")


@dataclass(frozen=True)
class PortfolioIntelligenceReport:
    leverage: float
    estimated_annual_volatility: float
    drawdown_scale: float
    stress_scale: float
    confidence_scale: float
    correlation_scale: float
    max_pair_correlation: float
    stress_detected: bool


def estimate_portfolio_volatility(
    weights: pd.Series,
    returns: pd.DataFrame,
    periods_per_year: int = 252,
) -> float:
    aligned = returns.loc[:, weights.index].dropna()
    if aligned.empty:
        return 0.0
    cov = aligned.cov().to_numpy(dtype=float) * periods_per_year
    w = weights.to_numpy(dtype=float)
    variance = float(w.T @ cov @ w)
    return float(np.sqrt(max(0.0, variance)))



def _active_max_pair_correlation(
    weights: pd.Series,
    returns: pd.DataFrame,
) -> float:
    active_assets = [asset for asset in weights.index if abs(float(weights.loc[asset])) > 1e-12]
    if len(active_assets) < 2:
        return 0.0

    aligned = returns.loc[:, active_assets].dropna()
    if aligned.empty:
        return 0.0

    corr = aligned.corr().abs()
    max_corr = 0.0
    for i, asset in enumerate(corr.index):
        for other in corr.columns[i + 1 :]:
            value = corr.at[asset, other]
            if pd.notna(value):
                max_corr = max(max_corr, float(value))
    return max_corr


def _correlation_scale(
    max_pair_correlation: float,
    config: PortfolioIntelligenceConfig,
) -> float:
    if max_pair_correlation <= config.correlation_soft_limit:
        return 1.0
    if max_pair_correlation >= config.correlation_hard_limit:
        return config.min_leverage

    span = config.correlation_hard_limit - config.correlation_soft_limit
    if span <= 0:
        return config.min_leverage
    progress = (max_pair_correlation - config.correlation_soft_limit) / span
    return 1.0 - progress * (1.0 - config.min_leverage)

def _drawdown_scale(
    current_equity: float,
    peak_equity: float,
    config: PortfolioIntelligenceConfig,
) -> float:
    if peak_equity <= 0:
        return 1.0
    drawdown = max(0.0, 1.0 - current_equity / peak_equity)
    if drawdown <= config.drawdown_soft_limit:
        return 1.0
    if drawdown >= config.drawdown_hard_limit:
        return config.min_leverage

    span = config.drawdown_hard_limit - config.drawdown_soft_limit
    progress = (drawdown - config.drawdown_soft_limit) / span
    return 1.0 - progress * (1.0 - config.min_leverage)


def apply_portfolio_intelligence(
    base_weights: pd.Series,
    returns: pd.DataFrame,
    confidences: dict[str, float],
    *,
    current_equity: float,
    peak_equity: float,
    config: PortfolioIntelligenceConfig | None = None,
) -> tuple[pd.Series, PortfolioIntelligenceReport]:
    config = config or PortfolioIntelligenceConfig()
    weights = base_weights.astype(float).copy()

    confidence_multipliers = pd.Series(0.0, index=weights.index, dtype=float)
    for asset in weights.index:
        confidence = float(confidences.get(asset, 0.0))
        if confidence <= config.confidence_floor:
            confidence_multipliers.loc[asset] = 0.0
        else:
            normalized = (confidence - config.confidence_floor) / (1.0 - config.confidence_floor)
            confidence_multipliers.loc[asset] = normalized ** config.confidence_power

    weights *= confidence_multipliers
    gross = float(weights.abs().sum())
    if gross > 0:
        weights /= gross

    estimated_vol = estimate_portfolio_volatility(weights, returns)
    if estimated_vol <= 1e-12:
        vol_scale = config.min_leverage
    else:
        vol_scale = config.target_annual_volatility / estimated_vol

    recent_vol = returns.tail(20).std(ddof=1).mean()
    baseline_vol = returns.tail(120).std(ddof=1).mean()
    stress_detected = bool(
        pd.notna(recent_vol)
        and pd.notna(baseline_vol)
        and baseline_vol > 0
        and recent_vol >= baseline_vol * config.stress_vol_multiplier
    )
    stress_scale = 0.5 if stress_detected else 1.0
    drawdown_scale = _drawdown_scale(current_equity, peak_equity, config)
    max_pair_correlation = _active_max_pair_correlation(weights, returns)
    correlation_scale = _correlation_scale(max_pair_correlation, config)

    confidence_scale = float(confidence_multipliers.mean()) if len(confidence_multipliers) else 0.0
    base_leverage = min(
        config.max_leverage,
        max(
            config.min_leverage,
            vol_scale * drawdown_scale * stress_scale,
        ),
    )
    leverage = max(
        config.min_leverage,
        min(base_leverage, correlation_scale),
    )

    intelligent_weights = weights * leverage
    return intelligent_weights, PortfolioIntelligenceReport(
        leverage=float(leverage),
        estimated_annual_volatility=float(estimated_vol),
        drawdown_scale=float(drawdown_scale),
        stress_scale=float(stress_scale),
        confidence_scale=confidence_scale,
        correlation_scale=float(correlation_scale),
        max_pair_correlation=float(max_pair_correlation),
        stress_detected=stress_detected,
    )

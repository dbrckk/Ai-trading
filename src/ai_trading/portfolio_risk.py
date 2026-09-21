from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class PortfolioRiskConfig:
    max_gross_exposure: float = 1.00
    max_net_exposure: float = 0.75
    max_asset_exposure: float = 0.35
    max_pair_correlation: float = 0.90

    def __post_init__(self) -> None:
        if self.max_gross_exposure <= 0:
            raise ValueError("max_gross_exposure must be positive")
        if self.max_net_exposure <= 0 or self.max_net_exposure > self.max_gross_exposure:
            raise ValueError("max_net_exposure must be in (0, max_gross_exposure]")
        if self.max_asset_exposure <= 0 or self.max_asset_exposure > self.max_gross_exposure:
            raise ValueError("max_asset_exposure must be in (0, max_gross_exposure]")
        if not 0.0 <= self.max_pair_correlation <= 1.0:
            raise ValueError("max_pair_correlation must be in [0, 1]")


@dataclass(frozen=True)
class PortfolioRiskReport:
    approved: bool
    gross_exposure: float
    net_exposure: float
    max_asset_exposure: float
    max_pair_correlation: float
    reasons: tuple[str, ...]


def evaluate_portfolio_risk(
    notionals: pd.Series,
    equity: float,
    returns: pd.DataFrame,
    config: PortfolioRiskConfig | None = None,
) -> PortfolioRiskReport:
    config = config or PortfolioRiskConfig()
    if equity <= 0:
        raise ValueError("equity must be positive")

    exposures = notionals.astype(float) / equity
    gross = float(exposures.abs().sum())
    net = float(abs(exposures.sum()))
    max_asset = float(exposures.abs().max()) if len(exposures) else 0.0

    corr = returns.astype(float).corr().abs()
    max_corr = 0.0
    if corr.shape[0] > 1:
        for i, a in enumerate(corr.index):
            for b in corr.columns[i + 1 :]:
                value = corr.at[a, b]
                if pd.notna(value):
                    max_corr = max(max_corr, float(value))

    reasons: list[str] = []
    if gross > config.max_gross_exposure + 1e-12:
        reasons.append("gross exposure limit exceeded")
    if net > config.max_net_exposure + 1e-12:
        reasons.append("net exposure limit exceeded")
    if max_asset > config.max_asset_exposure + 1e-12:
        reasons.append("single-asset exposure limit exceeded")
    if max_corr > config.max_pair_correlation + 1e-12:
        reasons.append("pair correlation limit exceeded")

    return PortfolioRiskReport(
        approved=not reasons,
        gross_exposure=gross,
        net_exposure=net,
        max_asset_exposure=max_asset,
        max_pair_correlation=max_corr,
        reasons=tuple(reasons),
    )

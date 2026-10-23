from __future__ import annotations

from dataclasses import dataclass
from math import isfinite

import pandas as pd


@dataclass(frozen=True)
class PortfolioRiskConfig:
    max_gross_exposure: float = 1.00
    max_net_exposure: float = 0.75
    max_asset_exposure: float = 0.35
    max_pair_correlation: float = 0.90

    def __post_init__(self) -> None:
        if not isfinite(self.max_gross_exposure) or self.max_gross_exposure <= 0:
            raise ValueError("max_gross_exposure must be positive and finite")
        if (
            not isfinite(self.max_net_exposure)
            or self.max_net_exposure <= 0
            or self.max_net_exposure > self.max_gross_exposure
        ):
            raise ValueError("max_net_exposure must be in (0, max_gross_exposure]")
        if (
            not isfinite(self.max_asset_exposure)
            or self.max_asset_exposure <= 0
            or self.max_asset_exposure > self.max_gross_exposure
        ):
            raise ValueError("max_asset_exposure must be in (0, max_gross_exposure]")
        if not isfinite(self.max_pair_correlation) or not 0.0 <= self.max_pair_correlation <= 1.0:
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
    if not isfinite(equity) or equity <= 0:
        raise ValueError("equity must be positive and finite")

    notionals_numeric = notionals.astype(float)
    if not all(isfinite(value) for value in notionals_numeric):
        raise ValueError("notionals must be finite")
    exposures = notionals_numeric / equity
    gross = float(exposures.abs().sum())
    net = float(abs(exposures.sum()))
    max_asset = float(exposures.abs().max()) if len(exposures) else 0.0
    if not all(isfinite(value) for value in (gross, net, max_asset)):
        raise ValueError("portfolio exposures must be finite")

    # Missing/constant return series cannot prove that two held positions
    # are decorrelated. Do not silently treat undefined correlation as zero.
    active_assets = notionals_numeric.index[notionals_numeric.ne(0.0)]
    missing_evidence = len(active_assets) > 1 and (
        not active_assets.is_unique
        or not set(active_assets).issubset(returns.columns)
        or not returns.columns.is_unique
    )
    max_corr = 0.0
    if len(active_assets) > 1 and not missing_evidence:
        corr = returns.loc[:, active_assets].astype(float).corr().abs()
        for i, asset in enumerate(active_assets):
            for other in active_assets[i + 1 :]:
                value = float(corr.at[asset, other])
                if not isfinite(value):
                    missing_evidence = True
                else:
                    max_corr = max(max_corr, value)

    reasons: list[str] = []
    if missing_evidence:
        reasons.append("insufficient pair correlation evidence")
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

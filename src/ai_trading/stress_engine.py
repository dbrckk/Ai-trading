from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class StressScenario:
    name: str
    volatility_multiplier: float = 1.0
    correlation_multiplier: float = 1.0
    gap_shock: float = 0.0
    slippage_bps: float = 0.0
    liquidity_scale: float = 1.0


@dataclass(frozen=True)
class StressPolicy:
    max_loss: float = 0.08
    max_stressed_cvar: float = 0.06
    monte_carlo_paths: int = 2000
    horizon_days: int = 5
    random_state: int = 42


@dataclass(frozen=True)
class StressReport:
    worst_loss: float
    stressed_cvar: float
    risk_scale: float
    approved: bool
    worst_scenario: str
    scenario_losses: dict[str, float]


DEFAULT_SCENARIOS = (
    StressScenario("vol_x2", volatility_multiplier=2.0),
    StressScenario("vol_x3", volatility_multiplier=3.0),
    StressScenario("corr_spike", correlation_multiplier=1.75),
    StressScenario("gap_down", gap_shock=-0.05),
    StressScenario(
        "liquidity_crunch",
        volatility_multiplier=2.0,
        slippage_bps=50.0,
        liquidity_scale=0.5,
    ),
)


def _stressed_covariance(
    returns: pd.DataFrame,
    scenario: StressScenario,
) -> np.ndarray:
    clean = returns.astype(float).dropna()
    cov = clean.cov().to_numpy(dtype=float)
    std = np.sqrt(np.clip(np.diag(cov), 0.0, None))
    corr = clean.corr().fillna(0.0).to_numpy(dtype=float)
    stressed_corr = np.eye(len(std)) + (corr - np.eye(len(std))) * scenario.correlation_multiplier
    stressed_corr = np.clip(stressed_corr, -0.99, 0.99)
    np.fill_diagonal(stressed_corr, 1.0)
    stressed_std = std * scenario.volatility_multiplier
    return np.outer(stressed_std, stressed_std) * stressed_corr


def run_stress_test(
    returns: pd.DataFrame,
    weights: pd.Series,
    *,
    scenarios: tuple[StressScenario, ...] = DEFAULT_SCENARIOS,
    policy: StressPolicy | None = None,
) -> StressReport:
    policy = policy or StressPolicy()
    aligned = returns.loc[:, weights.index].dropna()
    if len(aligned) < 30:
        raise ValueError("Need at least 30 aligned observations for stress testing")

    w = weights.astype(float).to_numpy(dtype=float)
    mean = aligned.mean().to_numpy(dtype=float)
    rng = np.random.default_rng(policy.random_state)

    scenario_losses: dict[str, float] = {}
    all_losses: list[float] = []

    for scenario in scenarios:
        cov = _stressed_covariance(aligned, scenario)
        sims = rng.multivariate_normal(
            mean=mean,
            cov=cov,
            size=(policy.monte_carlo_paths, policy.horizon_days),
            check_valid="ignore",
        )
        portfolio = np.einsum("phn,n->ph", sims, w)
        compounded = np.prod(1.0 + portfolio, axis=1) - 1.0
        compounded += scenario.gap_shock * float(np.sum(np.abs(w)))
        compounded -= (
            scenario.slippage_bps
            / 10_000.0
            * float(np.sum(np.abs(w)))
            / max(1e-6, scenario.liquidity_scale)
        )

        losses = -compounded
        all_losses.extend(float(x) for x in losses)
        scenario_losses[scenario.name] = float(np.quantile(losses, 0.99))

    loss_series = pd.Series(all_losses, dtype=float)
    cutoff = float(loss_series.quantile(0.95))
    stressed_cvar = float(loss_series[loss_series >= cutoff].mean())
    worst_scenario = max(scenario_losses, key=scenario_losses.get)
    worst_loss = float(scenario_losses[worst_scenario])

    scale_candidates = [1.0]
    if worst_loss > 0:
        scale_candidates.append(policy.max_loss / worst_loss)
    if stressed_cvar > 0:
        scale_candidates.append(policy.max_stressed_cvar / stressed_cvar)
    risk_scale = float(np.clip(min(scale_candidates), 0.0, 1.0))

    approved = worst_loss <= policy.max_loss and stressed_cvar <= policy.max_stressed_cvar
    return StressReport(
        worst_loss=worst_loss,
        stressed_cvar=stressed_cvar,
        risk_scale=risk_scale,
        approved=approved,
        worst_scenario=worst_scenario,
        scenario_losses=scenario_losses,
    )

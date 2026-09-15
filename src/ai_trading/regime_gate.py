from __future__ import annotations

from dataclasses import dataclass

from .backtest import BacktestReport


@dataclass(frozen=True)
class RegimeGatePolicy:
    min_observed_regimes: int = 2
    min_regime_return: float = -0.10
    max_regime_return_spread: float = 0.50


@dataclass(frozen=True)
class RegimeGateResult:
    passed: bool
    observed_regimes: int
    worst_regime: str | None
    worst_return: float | None
    return_spread: float
    reasons: tuple[str, ...]


def evaluate_regime_gate(
    report: BacktestReport,
    policy: RegimeGatePolicy | None = None,
) -> RegimeGateResult:
    policy = policy or RegimeGatePolicy()
    returns = report.regime_returns
    reasons: list[str] = []

    if len(returns) < policy.min_observed_regimes:
        reasons.append("insufficient regime coverage")

    worst_regime = min(returns, key=returns.get) if returns else None
    worst_return = returns[worst_regime] if worst_regime is not None else None
    if worst_return is not None and worst_return < policy.min_regime_return:
        reasons.append("worst regime return below threshold")

    spread = max(returns.values()) - min(returns.values()) if returns else 0.0
    if spread > policy.max_regime_return_spread:
        reasons.append("regime return dispersion above threshold")

    return RegimeGateResult(
        passed=not reasons,
        observed_regimes=len(returns),
        worst_regime=worst_regime,
        worst_return=worst_return,
        return_spread=spread,
        reasons=tuple(reasons),
    )

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class EconomicMetaConfig:
    pnl_weight: float = 1.0
    turnover_penalty: float = 0.20
    cost_penalty: float = 1.0
    drawdown_penalty: float = 0.75
    decay: float = 0.97
    exploration_floor: float = 0.05


@dataclass(frozen=True)
class EconomicMetaStats:
    score: float = 0.0
    decayed_pnl: float = 0.0
    decayed_turnover: float = 0.0
    decayed_costs: float = 0.0
    decayed_drawdown: float = 0.0
    observations: int = 0


def update_economic_meta(
    stats: EconomicMetaStats,
    *,
    pnl: float,
    turnover: float,
    costs: float,
    drawdown: float,
    equity: float,
    config: EconomicMetaConfig | None = None,
) -> EconomicMetaStats:
    config = config or EconomicMetaConfig()
    if equity <= 0:
        raise ValueError("equity must be positive")

    d = float(np.clip(config.decay, 0.0, 1.0))
    decayed_pnl = d * stats.decayed_pnl + float(pnl) / equity
    decayed_turnover = d * stats.decayed_turnover + abs(float(turnover)) / equity
    decayed_costs = d * stats.decayed_costs + abs(float(costs)) / equity
    decayed_drawdown = d * stats.decayed_drawdown + max(0.0, float(drawdown))

    score = (
        config.pnl_weight * decayed_pnl
        - config.turnover_penalty * decayed_turnover
        - config.cost_penalty * decayed_costs
        - config.drawdown_penalty * decayed_drawdown
    )

    return EconomicMetaStats(
        score=float(score),
        decayed_pnl=decayed_pnl,
        decayed_turnover=decayed_turnover,
        decayed_costs=decayed_costs,
        decayed_drawdown=decayed_drawdown,
        observations=stats.observations + 1,
    )


def economic_route_weight(
    stats: EconomicMetaStats,
    *,
    config: EconomicMetaConfig | None = None,
) -> float:
    config = config or EconomicMetaConfig()
    # Smooth positive mapping with an exploration floor.
    mapped = 1.0 / (1.0 + np.exp(-stats.score * 10.0))
    return float(max(config.exploration_floor, mapped))

from __future__ import annotations

from dataclasses import dataclass, replace

import pandas as pd

from .backtest import BacktestReport, WalkForwardBacktester
from .config import RiskConfig


@dataclass(frozen=True)
class CostStressScenario:
    name: str
    transaction_cost_bps: float
    slippage_bps: float


@dataclass(frozen=True)
class CostStressResult:
    scenario: CostStressScenario
    total_return: float
    excess_return: float
    sharpe: float
    max_drawdown: float
    trades: int


DEFAULT_COST_STRESS_SCENARIOS = (
    CostStressScenario("base", 1.0, 2.0),
    CostStressScenario("elevated", 2.0, 5.0),
    CostStressScenario("severe", 5.0, 10.0),
)


def run_cost_stress(
    backtester: WalkForwardBacktester,
    df: pd.DataFrame,
    *,
    scenarios: tuple[CostStressScenario, ...] = DEFAULT_COST_STRESS_SCENARIOS,
) -> tuple[CostStressResult, ...]:
    results: list[CostStressResult] = []
    for scenario in scenarios:
        risk = replace(
            backtester.risk_config,
            transaction_cost_bps=scenario.transaction_cost_bps,
            slippage_bps=scenario.slippage_bps,
        )
        stressed = WalkForwardBacktester(
            risk_config=risk,
            model_config=backtester.model_config,
            config=backtester.config,
        ).run(df)
        results.append(_result(scenario, stressed))
    return tuple(results)


def _result(scenario: CostStressScenario, report: BacktestReport) -> CostStressResult:
    return CostStressResult(
        scenario=scenario,
        total_return=report.metrics.total_return,
        excess_return=report.excess_return,
        sharpe=report.metrics.sharpe,
        max_drawdown=report.metrics.max_drawdown,
        trades=report.trades,
    )


def risk_config_for_scenario(
    config: RiskConfig,
    scenario: CostStressScenario,
) -> RiskConfig:
    return replace(
        config,
        transaction_cost_bps=scenario.transaction_cost_bps,
        slippage_bps=scenario.slippage_bps,
    )

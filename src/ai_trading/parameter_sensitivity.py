from __future__ import annotations

from dataclasses import dataclass, replace

import pandas as pd

from .backtest import BacktestReport, WalkForwardBacktester


@dataclass(frozen=True)
class SensitivityScenario:
    name: str
    confidence_multiplier: float = 1.0
    threshold_multiplier: float = 1.0
    position_multiplier: float = 1.0


@dataclass(frozen=True)
class SensitivityResult:
    scenario: SensitivityScenario
    total_return: float
    excess_return: float
    sharpe: float
    max_drawdown: float
    trades: int


DEFAULT_SENSITIVITY_SCENARIOS = (
    SensitivityScenario("confidence_down", confidence_multiplier=0.95),
    SensitivityScenario("confidence_up", confidence_multiplier=1.05),
    SensitivityScenario("threshold_down", threshold_multiplier=0.80),
    SensitivityScenario("threshold_up", threshold_multiplier=1.20),
    SensitivityScenario("position_down", position_multiplier=0.80),
    SensitivityScenario("position_up", position_multiplier=1.20),
)


def run_parameter_sensitivity(
    backtester: WalkForwardBacktester,
    df: pd.DataFrame,
    *,
    scenarios: tuple[
        SensitivityScenario, ...
    ] = DEFAULT_SENSITIVITY_SCENARIOS,
) -> tuple[SensitivityResult, ...]:
    results: list[SensitivityResult] = []
    for scenario in scenarios:
        risk = replace(
            backtester.risk_config,
            min_confidence=_bounded(
                backtester.risk_config.min_confidence
                * scenario.confidence_multiplier,
                0.01,
                0.99,
            ),
            max_position_fraction=_bounded(
                backtester.risk_config.max_position_fraction
                * scenario.position_multiplier,
                0.001,
                1.0,
            ),
        )
        model = replace(
            backtester.model_config,
            return_threshold=max(
                1e-8,
                backtester.model_config.return_threshold
                * scenario.threshold_multiplier,
            ),
        )
        report = WalkForwardBacktester(
            risk_config=risk,
            model_config=model,
            config=backtester.config,
        ).run(df)
        results.append(_result(scenario, report))
    return tuple(results)


def _bounded(value: float, lower: float, upper: float) -> float:
    return max(lower, min(upper, value))


def _result(
    scenario: SensitivityScenario,
    report: BacktestReport,
) -> SensitivityResult:
    return SensitivityResult(
        scenario=scenario,
        total_return=report.metrics.total_return,
        excess_return=report.excess_return,
        sharpe=report.metrics.sharpe,
        max_drawdown=report.metrics.max_drawdown,
        trades=report.trades,
    )

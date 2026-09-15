import pandas as pd

from ai_trading import cost_stress
from ai_trading.backtest import BacktestReport
from ai_trading.config import RiskConfig
from ai_trading.cost_stress import CostStressScenario, run_cost_stress
from ai_trading.performance import PerformanceMetrics


class FakeBacktester:
    def __init__(self, *, risk_config, model_config=None, config=None) -> None:
        self.risk_config = risk_config
        self.model_config = model_config
        self.config = config

    def run(self, df) -> BacktestReport:
        bps = self.risk_config.transaction_cost_bps + self.risk_config.slippage_bps
        total = 0.20 - bps / 1000.0
        metrics = PerformanceMetrics(
            total_return=total,
            annualized_return=total,
            annualized_volatility=0.1,
            sharpe=1.0,
            sortino=1.2,
            max_drawdown=0.1,
            calmar=1.0,
        )
        curve = pd.Series([100.0, 101.0])
        return BacktestReport(
            metrics=metrics,
            benchmark_metrics=metrics,
            excess_return=total - 0.10,
            trades=10,
            decisions=20,
            rejected_decisions=0,
            folds=4,
            equity_curve=curve,
            benchmark_curve=curve,
            regime_returns={},
        )


def test_cost_stress_applies_each_cost_scenario(monkeypatch) -> None:
    monkeypatch.setattr(cost_stress, "WalkForwardBacktester", FakeBacktester)
    base = FakeBacktester(risk_config=RiskConfig())
    scenarios = (
        CostStressScenario("base", 1.0, 2.0),
        CostStressScenario("severe", 5.0, 10.0),
    )

    results = run_cost_stress(base, pd.DataFrame(), scenarios=scenarios)

    assert [result.scenario.name for result in results] == ["base", "severe"]
    assert results[1].total_return < results[0].total_return
    assert results[1].excess_return < results[0].excess_return

from __future__ import annotations

from dataclasses import asdict, dataclass

import pandas as pd

from .broker import PaperBroker
from .config import ModelConfig, RiskConfig
from .features import FEATURES, make_features, make_labels
from .ensemble import EnsembleDirectionModel
from .model import OnlineDirectionModel
from .regime import detect_regime
from .performance import PerformanceMetrics, buy_and_hold_equity, compute_metrics
from .risk import PortfolioSnapshot, RiskEngine


@dataclass(frozen=True)
class WalkForwardConfig:
    min_train_bars: int = 252
    test_window_bars: int = 63
    max_train_bars: int | None = 1000
    periods_per_year: int = 252
    use_ensemble: bool = False

    def as_dict(self) -> dict[str, int | None]:
        return asdict(self)


@dataclass(frozen=True)
class BacktestReport:
    metrics: PerformanceMetrics
    benchmark_metrics: PerformanceMetrics
    excess_return: float
    trades: int
    decisions: int
    rejected_decisions: int
    folds: int
    equity_curve: pd.Series
    benchmark_curve: pd.Series


class WalkForwardBacktester:
    """Purged walk-forward simulation with next-bar-open execution."""

    def __init__(
        self,
        *,
        risk_config: RiskConfig,
        model_config: ModelConfig,
        config: WalkForwardConfig | None = None,
    ) -> None:
        self.risk_config = risk_config
        self.model_config = model_config
        self.config = config or WalkForwardConfig()
        self.risk = RiskEngine(risk_config)

    def run(self, df: pd.DataFrame) -> BacktestReport:
        features = make_features(df)
        labels = make_labels(
            df,
            horizon_bars=self.model_config.horizon_bars,
            return_threshold=self.model_config.return_threshold,
        )
        usable = features.dropna().index.intersection(labels.dropna().index)

        minimum = self.config.min_train_bars + self.config.test_window_bars + 1
        if len(usable) < minimum:
            raise ValueError(f"Need at least {minimum} usable bars for walk-forward backtest")

        broker = PaperBroker(self.risk_config)
        curve: dict[pd.Timestamp, float] = {}
        benchmark_prices: dict[pd.Timestamp, float] = {}
        trades = 0
        decisions = 0
        rejected = 0
        folds = 0
        previous_units = broker.state.units

        purge = max(1, self.model_config.horizon_bars)
        start = self.config.min_train_bars + purge
        while start < len(usable) - 1:
            test_end = min(start + self.config.test_window_bars, len(usable) - 1)
            train_end = max(0, start - purge)
            train_start = 0
            if self.config.max_train_bars is not None:
                train_start = max(0, train_end - self.config.max_train_bars)

            train_idx = usable[train_start:train_end]
            test_idx = usable[start:test_end]
            if len(train_idx) < self.config.min_train_bars or len(test_idx) == 0:
                break

            if self.config.use_ensemble:
                model = EnsembleDirectionModel(random_state=42 + folds)
            else:
                model = OnlineDirectionModel(random_state=42 + folds)
            model.fit(features.loc[train_idx], labels.loc[train_idx])
            folds += 1

            for signal_idx in test_idx:
                signal_pos = int(df.index.get_loc(signal_idx))
                if signal_pos + 1 >= len(df.index):
                    continue

                execution_idx = df.index[signal_pos + 1]
                execution_price = float(df.at[execution_idx, "Open"])
                close_price = float(df.at[execution_idx, "Close"])

                broker.mark(execution_price)
                feature_row = features.loc[signal_idx, FEATURES]
                if self.config.use_ensemble:
                    prediction = model.predict_one(feature_row, detect_regime(feature_row))
                else:
                    prediction = model.predict_one(feature_row)
                snapshot = PortfolioSnapshot(
                    equity=broker.state.equity,
                    peak_equity=broker.state.peak_equity,
                    day_start_equity=broker.state.day_start_equity,
                    current_position_value=broker.state.units * execution_price,
                )
                decision = self.risk.evaluate(prediction, snapshot)
                decisions += 1

                if decision.approved:
                    broker.rebalance(decision.side, decision.target_notional, execution_price)
                    if broker.state.units != previous_units:
                        trades += 1
                        previous_units = broker.state.units
                else:
                    rejected += 1

                broker.mark(close_price)
                curve[execution_idx] = broker.state.equity
                benchmark_prices[execution_idx] = close_price

            start = test_end

        if len(curve) < 2:
            raise ValueError("Walk-forward produced insufficient out-of-sample observations")

        equity = pd.Series(curve, dtype=float).sort_index()
        benchmark_price_series = pd.Series(benchmark_prices, dtype=float).sort_index()
        benchmark = buy_and_hold_equity(
            benchmark_price_series.reindex(equity.index),
            self.risk_config.starting_cash,
        )

        metrics = compute_metrics(equity, self.config.periods_per_year)
        benchmark_metrics = compute_metrics(benchmark, self.config.periods_per_year)

        return BacktestReport(
            metrics=metrics,
            benchmark_metrics=benchmark_metrics,
            excess_return=metrics.total_return - benchmark_metrics.total_return,
            trades=trades,
            decisions=decisions,
            rejected_decisions=rejected,
            folds=folds,
            equity_curve=equity,
            benchmark_curve=benchmark,
        )

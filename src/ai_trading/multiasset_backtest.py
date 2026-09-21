from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from .config import ModelConfig, RiskConfig
from .ensemble import EnsembleDirectionModel
from .features import FEATURES, make_features, make_labels
from .performance import PerformanceMetrics, compute_metrics, infer_periods_per_year
from .portfolio import AllocationConfig, inverse_volatility_weights, target_notionals
from .portfolio_intelligence import PortfolioIntelligenceConfig, apply_portfolio_intelligence
from .paper_execution import calculate_rebalance_fill
from .portfolio_risk import PortfolioRiskConfig, evaluate_portfolio_risk
from .regime import detect_regime


@dataclass(frozen=True)
class MultiAssetBacktestReport:
    metrics: PerformanceMetrics
    equity_curve: pd.Series
    trades: int
    decisions: int
    rejected_rebalances: int


class MultiAssetWalkForwardBacktester:
    def __init__(
        self,
        *,
        risk_config: RiskConfig | None = None,
        model_config: ModelConfig | None = None,
        allocation_config: AllocationConfig | None = None,
        portfolio_risk_config: PortfolioRiskConfig | None = None,
        intelligence_config: PortfolioIntelligenceConfig | None = None,
        min_train_bars: int = 252,
        test_window_bars: int = 63,
    ) -> None:
        self.risk_config = risk_config or RiskConfig()
        self.model_config = model_config or ModelConfig()
        self.allocation_config = allocation_config or AllocationConfig()
        self.portfolio_risk_config = portfolio_risk_config or PortfolioRiskConfig()
        self.intelligence_config = intelligence_config or PortfolioIntelligenceConfig()
        self.min_train_bars = min_train_bars
        self.test_window_bars = test_window_bars

    def run(self, markets: dict[str, pd.DataFrame]) -> MultiAssetBacktestReport:
        if len(markets) < 2:
            raise ValueError("Need at least two assets")

        common = None
        for df in markets.values():
            common = df.index if common is None else common.intersection(df.index)
        if common is None or len(common) < self.min_train_bars + self.test_window_bars + 5:
            raise ValueError("Insufficient aligned history")

        aligned = {
            symbol: df.loc[common].copy()
            for symbol, df in markets.items()
        }
        features = {s: make_features(df) for s, df in aligned.items()}
        labels = {
            s: make_labels(
                df,
                horizon_bars=self.model_config.horizon_bars,
                return_threshold=self.model_config.return_threshold,
            )
            for s, df in aligned.items()
        }
        closes = pd.DataFrame({s: df["Close"].astype(float) for s, df in aligned.items()})
        returns = closes.pct_change()

        cash = self.risk_config.starting_cash
        units = {s: 0.0 for s in aligned}
        last_prices = {s: float(aligned[s]["Close"].iloc[0]) for s in aligned}
        peak_equity = cash
        curve: dict[pd.Timestamp, float] = {}
        trades = 0
        decisions = 0
        rejected = 0

        purge = max(1, self.model_config.horizon_bars)
        start = self.min_train_bars + purge

        while start < len(common) - 1:
            test_end = min(start + self.test_window_bars, len(common) - 1)
            train_end = start - purge
            train_idx = common[:train_end]
            test_idx = common[start:test_end]

            models: dict[str, EnsembleDirectionModel] = {}
            for symbol in aligned:
                model = EnsembleDirectionModel(random_state=42)
                model.fit(features[symbol].loc[train_idx], labels[symbol].loc[train_idx])
                models[symbol] = model

            for signal_idx in test_idx:
                pos = int(common.get_loc(signal_idx))
                if pos + 1 >= len(common):
                    continue
                execution_idx = common[pos + 1]

                equity = cash + sum(units[s] * last_prices[s] for s in aligned)
                base_weights = inverse_volatility_weights(
                    returns.loc[:signal_idx].tail(120).dropna(),
                    self.allocation_config,
                )

                signals = {}
                confidences = {}
                signed = base_weights.copy()

                for symbol, model in models.items():
                    row = features[symbol].loc[signal_idx, FEATURES]
                    prediction = model.predict_one(row, detect_regime(row))
                    side = prediction.side if prediction.confidence >= self.risk_config.min_confidence else 0
                    signals[symbol] = side
                    confidences[symbol] = prediction.confidence
                    signed.loc[symbol] = base_weights.loc[symbol] * side

                intelligent, _ = apply_portfolio_intelligence(
                    signed,
                    returns.loc[:signal_idx].tail(120).dropna(),
                    confidences,
                    current_equity=equity,
                    peak_equity=peak_equity,
                    config=self.intelligence_config,
                )
                notionals = target_notionals(equity, intelligent)
                risk = evaluate_portfolio_risk(
                    notionals,
                    equity,
                    returns.loc[:signal_idx].tail(120).dropna(),
                    self.portfolio_risk_config,
                )
                decisions += 1

                if risk.approved:
                    for symbol in intelligent.index:
                        price = float(aligned[symbol].at[execution_idx, "Open"])
                        fill = calculate_rebalance_fill(
                            current_units=units[symbol],
                            target_notional=float(notionals[symbol]),
                            price=price,
                            transaction_cost_bps=self.risk_config.transaction_cost_bps,
                            slippage_bps=self.risk_config.slippage_bps,
                        )
                        cash -= fill.delta_units * price
                        cash -= fill.costs
                        if abs(fill.delta_units) > 1e-12:
                            trades += 1
                        units[symbol] = fill.desired_units
                else:
                    rejected += 1

                for symbol in aligned:
                    last_prices[symbol] = float(aligned[symbol].at[execution_idx, "Close"])

                equity = cash + sum(units[s] * last_prices[s] for s in aligned)
                peak_equity = max(peak_equity, equity)
                curve[execution_idx] = equity

            start = test_end

        equity_curve = pd.Series(curve, dtype=float).sort_index()
        if len(equity_curve) < 2:
            raise ValueError("Insufficient multi-asset out-of-sample observations")

        return MultiAssetBacktestReport(
            metrics=compute_metrics(
                equity_curve,
                infer_periods_per_year(equity_curve.index),
            ),
            equity_curve=equity_curve,
            trades=trades,
            decisions=decisions,
            rejected_rebalances=rejected,
        )

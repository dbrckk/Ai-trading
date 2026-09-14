from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from .broker import PaperBroker
from .config import ModelConfig, RiskConfig
from .features import FEATURES, make_features, make_labels
from .model import OnlineDirectionModel
from .risk import PortfolioSnapshot, RiskEngine


@dataclass(frozen=True)
class RunResult:
    starting_equity: float
    final_equity: float
    total_return: float
    max_drawdown: float
    trades: int
    decisions: int


class TradingEngine:
    def __init__(
        self,
        risk_config: RiskConfig | None = None,
        model_config: ModelConfig | None = None,
    ) -> None:
        self.risk_config = risk_config or RiskConfig()
        self.model_config = model_config or ModelConfig()
        self.model = OnlineDirectionModel()
        self.risk = RiskEngine(self.risk_config)

    def train(self, df: pd.DataFrame) -> None:
        x = make_features(df)
        y = make_labels(
            df,
            horizon_bars=self.model_config.horizon_bars,
            return_threshold=self.model_config.return_threshold,
        )
        self.model.fit(x, y)

    def paper_run(self, df: pd.DataFrame, train_fraction: float = 0.60) -> RunResult:
        if not 0.2 <= train_fraction <= 0.9:
            raise ValueError("train_fraction must be between 0.2 and 0.9")

        x = make_features(df)
        y = make_labels(
            df,
            horizon_bars=self.model_config.horizon_bars,
            return_threshold=self.model_config.return_threshold,
        )

        usable = x.dropna().index.intersection(y.dropna().index)
        if len(usable) < 100:
            raise ValueError("Need at least 100 usable bars")

        split = max(50, int(len(usable) * train_fraction))
        train_idx = usable[:split]
        test_idx = usable[split:]
        self.model.fit(x.loc[train_idx], y.loc[train_idx])

        broker = PaperBroker(self.risk_config)
        start = broker.state.equity
        max_dd = 0.0
        trades = 0
        decisions = 0
        previous_units = broker.state.units

        for idx in test_idx:
            price = float(df.at[idx, "Close"])
            broker.mark(price)

            prediction = self.model.predict_one(x.loc[idx, FEATURES])
            snapshot = PortfolioSnapshot(
                equity=broker.state.equity,
                peak_equity=broker.state.peak_equity,
                day_start_equity=broker.state.day_start_equity,
                current_position_value=broker.state.units * price,
            )
            decision = self.risk.evaluate(prediction, snapshot)
            decisions += 1

            if decision.approved:
                broker.rebalance(decision.side, decision.target_notional, price)
                if broker.state.units != previous_units:
                    trades += 1
                    previous_units = broker.state.units

            if broker.state.peak_equity > 0:
                dd = 1.0 - broker.state.equity / broker.state.peak_equity
                max_dd = max(max_dd, dd)

        if len(test_idx):
            broker.mark(float(df.at[test_idx[-1], "Close"]))

        final = broker.state.equity
        return RunResult(
            starting_equity=start,
            final_equity=final,
            total_return=final / start - 1.0,
            max_drawdown=max_dd,
            trades=trades,
            decisions=decisions,
        )

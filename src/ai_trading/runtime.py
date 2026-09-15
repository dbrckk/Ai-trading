from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path

import pandas as pd

from .audit import AuditLog
from .broker import PaperBroker
from .config import ModelConfig, RiskConfig
from .features import FEATURES, make_features, make_labels
from .model import Prediction
from .online import RiverDirectionModel
from .risk import PortfolioSnapshot, RiskEngine
from .runtime_lock import RuntimeLock
from .runtime_state import RuntimeState, RuntimeStateStore
from .trade_journal import TradeJournal, TradeSnapshot


@dataclass(frozen=True)
class RuntimeStepResult:
    processed: bool
    timestamp: str | None
    side: int
    confidence: float
    approved: bool
    reason: str
    equity: float
    units: float
    processed_bars: int
    retrain_due: bool


class PaperAutonomousRuntime:
    """One-step autonomous paper runtime.

    A scheduler may call step repeatedly. The runtime itself never routes
    real orders and never bypasses the independent risk engine.
    """

    def __init__(
        self,
        *,
        risk_config: RiskConfig | None = None,
        model_config: ModelConfig | None = None,
        state_store: RuntimeStateStore | None = None,
        audit_log: AuditLog | None = None,
        online_model_path: str | Path = "artifacts/models/online-river.joblib",
        lock_path: str | Path = "artifacts/runtime.lock",
        learning_cycle_every_bars: int = 63,
        trade_journal: TradeJournal | None = None,
        symbol: str = "UNKNOWN",
    ) -> None:
        self.risk_config = risk_config or RiskConfig()
        self.model_config = model_config or ModelConfig()
        self.state_store = state_store or RuntimeStateStore()
        self.audit = audit_log or AuditLog()
        self.online_model_path = Path(online_model_path)
        self.lock_path = Path(lock_path)
        self.learning_cycle_every_bars = learning_cycle_every_bars
        self.trade_journal = trade_journal or TradeJournal()
        self.symbol = symbol
        self.risk = RiskEngine(self.risk_config)

    def _load_online(self) -> RiverDirectionModel:
        import joblib

        if self.online_model_path.exists():
            return joblib.load(self.online_model_path)
        return RiverDirectionModel()

    def _save_online(self, model: RiverDirectionModel) -> None:
        import joblib

        self.online_model_path.parent.mkdir(parents=True, exist_ok=True)
        temp = self.online_model_path.with_suffix(".tmp")
        joblib.dump(model, temp)
        temp.replace(self.online_model_path)

    def _broker_from_state(self, state: RuntimeState) -> PaperBroker:
        broker = PaperBroker(self.risk_config)
        broker.state.cash = state.cash
        broker.state.units = state.units
        broker.state.last_price = state.last_price
        broker.state.peak_equity = state.peak_equity
        broker.state.day_start_equity = state.day_start_equity
        return broker

    @staticmethod
    def _state_from_broker(
        broker: PaperBroker,
        *,
        last_processed: str,
        processed_bars: int,
        last_learning_cycle_bar: int,
    ) -> RuntimeState:
        return RuntimeState(
            cash=broker.state.cash,
            units=broker.state.units,
            last_price=broker.state.last_price,
            peak_equity=broker.state.peak_equity,
            day_start_equity=broker.state.day_start_equity,
            last_processed=last_processed,
            processed_bars=processed_bars,
            last_learning_cycle_bar=last_learning_cycle_bar,
        )

    def step(self, df: pd.DataFrame) -> RuntimeStepResult:
        if len(df) < 40:
            raise ValueError("Need at least 40 bars for runtime features")

        with RuntimeLock(self.lock_path):
            features = make_features(df)
            labels = make_labels(
                df,
                horizon_bars=self.model_config.horizon_bars,
                return_threshold=self.model_config.return_threshold,
            )
            valid = features.dropna().index
            if len(valid) < 3:
                raise ValueError("Insufficient valid feature rows")

            signal_idx = valid[-2]
            signal_pos = int(df.index.get_loc(signal_idx))
            if signal_pos + 1 >= len(df.index):
                raise ValueError("No execution bar available after signal bar")
            execution_idx = df.index[signal_pos + 1]
            execution_time = str(execution_idx)
            state = self.state_store.load(self.risk_config.starting_cash)

            if state.last_processed == execution_time:
                broker = self._broker_from_state(state)
                return RuntimeStepResult(
                    processed=False,
                    timestamp=execution_time,
                    side=0,
                    confidence=0.0,
                    approved=False,
                    reason="bar already processed",
                    equity=broker.state.equity,
                    units=broker.state.units,
                    processed_bars=state.processed_bars,
                    retrain_due=False,
                )

            model = self._load_online()
            learn_idx = valid[-3]
            learn_label = labels.get(learn_idx)
            if pd.notna(learn_label):
                model.learn_one(
                    features.loc[learn_idx, FEATURES],
                    int(learn_label),
                )

            row = features.loc[signal_idx, FEATURES]
            prediction: Prediction = model.predict_one(row)

            execution_price = float(df.at[execution_idx, "Open"])
            close_price = float(df.at[execution_idx, "Close"])
            broker = self._broker_from_state(state)
            broker.mark(execution_price)
            broker.state.day_start_equity = broker.state.equity
            snapshot = PortfolioSnapshot(
                equity=broker.state.equity,
                peak_equity=broker.state.peak_equity,
                day_start_equity=broker.state.day_start_equity,
                current_position_value=broker.state.units * execution_price,
            )
            decision = self.risk.evaluate(prediction, snapshot)

            previous_units = broker.state.units
            if decision.approved:
                broker.rebalance(decision.side, decision.target_notional, execution_price)
                delta_units = broker.state.units - previous_units
                if abs(delta_units) > 1e-12:
                    self.trade_journal.append(
                        TradeSnapshot(
                            timestamp_utc=execution_time,
                            symbol=self.symbol,
                            side="BUY" if delta_units > 0 else "SELL",
                            quantity=abs(delta_units),
                            price=execution_price,
                            status="PAPER_FILLED",
                            confidence=prediction.confidence,
                            strategy="online-river",
                        )
                    )

            broker.mark(close_price)

            processed_bars = state.processed_bars + 1
            bars_since_cycle = processed_bars - state.last_learning_cycle_bar
            retrain_due = bars_since_cycle >= self.learning_cycle_every_bars

            new_state = self._state_from_broker(
                broker,
                last_processed=execution_time,
                processed_bars=processed_bars,
                last_learning_cycle_bar=state.last_learning_cycle_bar,
            )
            self.state_store.save(new_state)
            self._save_online(model)

            self.audit.append(
                "runtime_step",
                {
                    "signal_time": str(signal_idx),
                    "execution_time": execution_time,
                    "prediction": asdict(prediction),
                    "risk_decision": asdict(decision),
                    "equity": broker.state.equity,
                    "units": broker.state.units,
                    "processed_bars": processed_bars,
                    "retrain_due": retrain_due,
                },
            )

            return RuntimeStepResult(
                processed=True,
                timestamp=execution_time,
                side=prediction.side,
                confidence=prediction.confidence,
                approved=decision.approved,
                reason=decision.reason,
                equity=broker.state.equity,
                units=broker.state.units,
                processed_bars=processed_bars,
                retrain_due=retrain_due,
            )

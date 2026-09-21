from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path

import pandas as pd

from .audit import AuditLog
from .broker import PaperBroker
from .config import ModelConfig, RiskConfig
from .execution_costs import risk_config_for_symbol
from .features import FEATURES, make_features, make_labels
from .file_persistence import FilePaperPersistence
from .model import Prediction
from .model_codec import deserialize_model, serialize_model
from .mtf_shadow_challenger import MultiTimeframeShadowResult
from .online import RiverDirectionModel
from .persistence import CommitOutcome, PaperPersistence, RuntimeStepCommit
from .regime import detect_regime
from .risk import PortfolioSnapshot, RiskEngine
from .runtime_lock import RuntimeLock
from .runtime_state import RuntimeState, RuntimeStateStore
from .shadow_challenger import ShadowChallengerResult
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


@dataclass(frozen=True)
class PreparedRuntimeMarket:
    market: pd.DataFrame
    features: pd.DataFrame
    labels: pd.Series
    valid: pd.Index
    eligible: tuple[object, ...]


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
        persistence: PaperPersistence | None = None,
        runtime_key: str | None = None,
    ) -> None:
        base_risk_config = risk_config or RiskConfig()
        self.risk_config = (
            base_risk_config
            if risk_config is not None
            else risk_config_for_symbol(symbol, base_risk_config)
        )
        self.model_config = model_config or ModelConfig()
        self.state_store = state_store or RuntimeStateStore()
        self.audit = audit_log or AuditLog()
        self.online_model_path = Path(online_model_path)
        self.lock_path = Path(lock_path)
        self.learning_cycle_every_bars = learning_cycle_every_bars
        self.trade_journal = trade_journal or TradeJournal()
        self.symbol = symbol
        self.risk = RiskEngine(self.risk_config)
        self.persistence = persistence or FilePaperPersistence(
            state_store=self.state_store,
            trade_journal=self.trade_journal,
            audit_log=self.audit,
            model_path=self.online_model_path,
        )
        self.runtime_key = runtime_key or f"paper:{symbol}:legacy:online-river:v1"

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

    def _prepare_market_features(
        self,
        df: pd.DataFrame,
    ) -> tuple[pd.DataFrame, pd.Index, tuple[object, ...]]:
        if len(df) < 40:
            raise ValueError("Need at least 40 bars for runtime features")

        features = make_features(df)
        valid = features.dropna().index
        if len(valid) < 3:
            raise ValueError("Insufficient valid feature rows")

        execution: list[object] = []
        # Keep one valid row in reserve exactly as the legacy latest-bar path did.
        # A targeted signal also needs one prior valid row for online learning.
        for signal_idx in valid[1:-1]:
            signal_pos = int(df.index.get_loc(signal_idx))
            if signal_pos + 1 < len(df.index):
                execution.append(df.index[signal_pos + 1])
        return features, valid, tuple(dict.fromkeys(execution))

    def _eligible_execution_indices(self, df: pd.DataFrame) -> tuple[object, ...]:
        _, _, eligible = self._prepare_market_features(df)
        return eligible

    def prepare_market(self, df: pd.DataFrame) -> PreparedRuntimeMarket:
        features, valid, eligible = self._prepare_market_features(df)
        labels = make_labels(
            df,
            horizon_bars=self.model_config.horizon_bars,
            return_threshold=self.model_config.return_threshold,
        )
        return PreparedRuntimeMarket(
            market=df,
            features=features,
            labels=labels,
            valid=valid,
            eligible=eligible,
        )

    def step(self, df: pd.DataFrame) -> RuntimeStepResult:
        prepared = self.prepare_market(df)
        if not prepared.eligible:
            raise ValueError("No eligible execution bar available")
        return self.step_prepared(prepared, prepared.eligible[-1])

    def step_at(self, df: pd.DataFrame, execution_idx: object) -> RuntimeStepResult:
        features, valid, eligible = self._prepare_market_features(df)
        if execution_idx not in eligible:
            raise ValueError("Requested index is not an eligible execution bar")
        labels = make_labels(
            df,
            horizon_bars=self.model_config.horizon_bars,
            return_threshold=self.model_config.return_threshold,
        )
        prepared = PreparedRuntimeMarket(
            market=df,
            features=features,
            labels=labels,
            valid=valid,
            eligible=eligible,
        )
        return self.step_prepared(prepared, execution_idx)

    def step_prepared(
        self,
        prepared: PreparedRuntimeMarket,
        execution_idx: object,
        *,
        shadow_challenger: ShadowChallengerResult | None = None,
        mtf_shadow_challenger: MultiTimeframeShadowResult | None = None,
    ) -> RuntimeStepResult:
        if execution_idx not in prepared.eligible:
            raise ValueError("Requested index is not an eligible execution bar")

        with RuntimeLock(self.lock_path):
            return self._step_prepared_locked(
                prepared,
                execution_idx,
                shadow_challenger=shadow_challenger,
                mtf_shadow_challenger=mtf_shadow_challenger,
            )

    def _step_prepared_locked(
        self,
        prepared: PreparedRuntimeMarket,
        execution_idx: object,
        *,
        shadow_challenger: ShadowChallengerResult | None = None,
        mtf_shadow_challenger: MultiTimeframeShadowResult | None = None,
    ) -> RuntimeStepResult:
        df = prepared.market
        features = prepared.features
        labels = prepared.labels
        valid = prepared.valid
        eligible = prepared.eligible

        execution_pos = int(df.index.get_loc(execution_idx))
        if execution_pos < 1:
            raise ValueError("Requested index is not an eligible execution bar")
        signal_idx = df.index[execution_pos - 1]
        valid_positions = {value: index for index, value in enumerate(valid)}
        signal_valid_pos = valid_positions.get(signal_idx)
        if signal_valid_pos is None or signal_valid_pos < 1:
            raise ValueError("Requested index is not an eligible execution bar")
        learn_idx = valid[signal_valid_pos - 1]

        execution_time = str(execution_idx)
        persisted = self.persistence.load_runtime(
            self.runtime_key,
            self.risk_config.starting_cash,
        )
        state = persisted.state

        eligible_positions = {str(value): index for index, value in enumerate(eligible)}
        target_position = eligible_positions[execution_time]
        persisted_position = (
            eligible_positions.get(state.last_processed)
            if state.last_processed is not None
            else None
        )
        if persisted_position is not None and target_position <= persisted_position:
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

        if persisted.model is None:
            if not persisted.is_new and state.processed_bars > 0:
                raise ValueError("persisted runtime is missing its online model")
            model = RiverDirectionModel()
        else:
            model = deserialize_model(persisted.model)

        learn_label = labels.get(learn_idx)
        if pd.notna(learn_label):
            model.learn_one(
                features.loc[learn_idx, FEATURES],
                int(learn_label),
            )

        row = features.loc[signal_idx, FEATURES]
        observed_regime = detect_regime(row).name
        prediction: Prediction = model.predict_one(row)

        execution_price = float(df.at[execution_idx, "Open"])
        close_price = float(df.at[execution_idx, "Close"])
        broker = self._broker_from_state(state)
        broker.mark(execution_price)
        execution_day = pd.Timestamp(execution_idx).date()
        previous_day = (
            pd.Timestamp(state.last_processed).date()
            if state.last_processed is not None
            else None
        )
        if previous_day != execution_day:
            broker.reset_day_start()
        snapshot = PortfolioSnapshot(
            equity=broker.state.equity,
            peak_equity=broker.state.peak_equity,
            day_start_equity=broker.state.day_start_equity,
            current_position_value=broker.state.units * execution_price,
        )
        decision = self.risk.evaluate(prediction, snapshot)

        trade: TradeSnapshot | None = None
        previous_units = broker.state.units
        if decision.approved:
            broker.rebalance(decision.side, decision.target_notional, execution_price)
            delta_units = broker.state.units - previous_units
            if abs(delta_units) > 1e-12:
                trade = TradeSnapshot(
                    timestamp_utc=execution_time,
                    symbol=self.symbol,
                    side="BUY" if delta_units > 0 else "SELL",
                    quantity=abs(delta_units),
                    price=execution_price,
                    status="PAPER_FILLED",
                    confidence=prediction.confidence,
                    strategy="online-river",
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
        audit_payload = {
            "signal_time": str(signal_idx),
            "execution_time": execution_time,
            "prediction": asdict(prediction),
            "risk_decision": asdict(decision),
            "equity": broker.state.equity,
            "units": broker.state.units,
            "processed_bars": processed_bars,
            "retrain_due": retrain_due,
            "observed_regime": observed_regime,
        }
        if shadow_challenger is not None:
            audit_payload["shadow_challenger"] = asdict(shadow_challenger)
        if mtf_shadow_challenger is not None:
            audit_payload["mtf_shadow_challenger"] = asdict(mtf_shadow_challenger)
        outcome = self.persistence.commit_step(
            self.runtime_key,
            RuntimeStepCommit(
                expected_revision=persisted.revision,
                state=new_state,
                model=serialize_model(model),
                trade=trade,
                audit_event="runtime_step",
                audit_payload=audit_payload,
                observed_regime=observed_regime,
            ),
        )
        if outcome is CommitOutcome.CONFLICT:
            return RuntimeStepResult(
                processed=False,
                timestamp=execution_time,
                side=0,
                confidence=0.0,
                approved=False,
                reason="persistence revision conflict",
                equity=broker.state.equity,
                units=broker.state.units,
                processed_bars=state.processed_bars,
                retrain_due=False,
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

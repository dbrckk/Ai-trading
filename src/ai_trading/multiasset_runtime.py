from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import joblib
import pandas as pd

from .alpha_allocation import AlphaAllocationConfig, alpha_risk_weights
from .audit import AuditLog
from .config import ModelConfig, RiskConfig
from .ensemble import EnsembleDirectionModel
from .features import FEATURES, make_features, make_labels
from .meta_router import MetaContext, route_predictions
from .meta_store import MetaRouterStore
from .model_blend import BlendComponent, blend_predictions
from .model_quality import evaluate_model_quality
from .multiasset_state import AssetPosition, MultiAssetStateStore
from .online import RiverDirectionModel
from .pnl_attribution import attribute_pnl
from .portfolio import AllocationConfig, inverse_volatility_weights, target_notionals
from .portfolio_intelligence import (
    PortfolioIntelligenceConfig,
    apply_portfolio_intelligence,
)
from .portfolio_risk import PortfolioRiskConfig, evaluate_portfolio_risk
from .quality_store import QualityStore
from .regime import detect_regime
from .runtime_lock import RuntimeLock


@dataclass(frozen=True)
class MultiAssetStepResult:
    processed: bool
    timestamp: str | None
    equity: float
    cash: float
    weights: dict[str, float]
    notionals: dict[str, float]
    signals: dict[str, int]
    confidences: dict[str, float]
    risk_approved: bool
    risk_reasons: tuple[str, ...]


class MultiAssetPaperRuntime:
    def __init__(
        self,
        *,
        risk_config: RiskConfig | None = None,
        model_config: ModelConfig | None = None,
        allocation_config: AllocationConfig | None = None,
        portfolio_risk_config: PortfolioRiskConfig | None = None,
        state_store: MultiAssetStateStore | None = None,
        audit_log: AuditLog | None = None,
        lock_path: str = "artifacts/multiasset_runtime.lock",
        model_root: str | Path = "artifacts/models/multiasset",
        batch_model_root: str | Path = "artifacts/models/multiasset_batch",
        intelligence_config: PortfolioIntelligenceConfig | None = None,
        quality_store: QualityStore | None = None,
        alpha_allocation_config: AlphaAllocationConfig | None = None,
        meta_store: MetaRouterStore | None = None,
    ) -> None:
        self.risk_config = risk_config or RiskConfig()
        self.model_config = model_config or ModelConfig()
        self.allocation_config = allocation_config or AllocationConfig()
        self.portfolio_risk_config = portfolio_risk_config or PortfolioRiskConfig()
        self.state_store = state_store or MultiAssetStateStore()
        self.audit = audit_log or AuditLog("artifacts/multiasset_audit.jsonl")
        self.lock_path = lock_path
        self.model_root = Path(model_root)
        self.batch_model_root = Path(batch_model_root)
        self.intelligence_config = intelligence_config or PortfolioIntelligenceConfig()
        self.quality_store = quality_store or QualityStore()
        self.alpha_allocation_config = alpha_allocation_config or AlphaAllocationConfig()
        self.meta_store = meta_store or MetaRouterStore()

    def _batch_model_path(self, symbol: str) -> Path:
        safe = symbol.replace("/", "_").replace("=", "_").replace("^", "_")
        return self.batch_model_root / f"{safe}.joblib"

    def _load_or_train_batch_model(
        self,
        symbol: str,
        features: pd.DataFrame,
        labels: pd.Series,
        signal_idx,
    ) -> EnsembleDirectionModel:
        path = self._batch_model_path(symbol)
        if path.exists():
            return joblib.load(path)

        train_idx = features.index[features.index < signal_idx]
        train_idx = train_idx.intersection(labels.dropna().index)
        if len(train_idx) < 100:
            raise ValueError(f"Insufficient batch-model history for {symbol}")

        model = EnsembleDirectionModel(random_state=42)
        model.fit(features.loc[train_idx], labels.loc[train_idx])
        path.parent.mkdir(parents=True, exist_ok=True)
        temp = path.with_suffix(".tmp")
        joblib.dump(model, temp)
        temp.replace(path)
        return model

    def _model_path(self, symbol: str) -> Path:
        safe = symbol.replace("/", "_").replace("=", "_").replace("^", "_")
        return self.model_root / f"{safe}.joblib"

    def _load_model(self, symbol: str) -> RiverDirectionModel:
        path = self._model_path(symbol)
        if path.exists():
            return joblib.load(path)
        return RiverDirectionModel()

    def _save_model(self, symbol: str, model: RiverDirectionModel) -> None:
        path = self._model_path(symbol)
        path.parent.mkdir(parents=True, exist_ok=True)
        temp = path.with_suffix(".tmp")
        joblib.dump(model, temp)
        temp.replace(path)

    def step(self, markets: dict[str, pd.DataFrame]) -> MultiAssetStepResult:
        if len(markets) < 2:
            raise ValueError("Need at least two assets")

        with RuntimeLock(self.lock_path):
            closes = {}
            opens = {}
            execution_times: set[str] = set()
            features_by_symbol: dict[str, pd.DataFrame] = {}
            labels_by_symbol: dict[str, pd.Series] = {}

            for symbol, df in markets.items():
                if len(df) < 40:
                    raise ValueError(f"Insufficient data for {symbol}")
                closes[symbol] = df["Close"].astype(float)
                opens[symbol] = df["Open"].astype(float)
                execution_times.add(str(df.index[-1]))
                features_by_symbol[symbol] = make_features(df)
                labels_by_symbol[symbol] = make_labels(
                    df,
                    horizon_bars=self.model_config.horizon_bars,
                    return_threshold=self.model_config.return_threshold,
                )

            if len(execution_times) != 1:
                raise ValueError("Assets are not aligned on the same latest bar")
            execution_time = next(iter(execution_times))

            state = self.state_store.load(self.risk_config.starting_cash)
            if state.last_processed == execution_time:
                return MultiAssetStepResult(
                    processed=False,
                    timestamp=execution_time,
                    equity=state.equity(),
                    cash=state.cash,
                    weights={},
                    notionals={},
                    signals={},
                    confidences={},
                    risk_approved=False,
                    risk_reasons=("bar already processed",),
                )

            close_frame = pd.DataFrame(closes).dropna()
            returns = close_frame.pct_change().dropna()
            if len(returns) < 20:
                raise ValueError("Insufficient aligned return history")

            base_weights = inverse_volatility_weights(returns, self.allocation_config)

            signals: dict[str, int] = {}
            confidences: dict[str, float] = {}
            signed_weights = base_weights.copy()

            for symbol in base_weights.index:
                features = features_by_symbol[symbol]
                labels = labels_by_symbol[symbol]
                valid = features.dropna().index
                if len(valid) < 3:
                    raise ValueError(f"Insufficient valid features for {symbol}")

                signal_idx = valid[-2]
                learn_idx = valid[-3]
                model = self._load_model(symbol)

                learn_label = labels.get(learn_idx)
                evaluation_prediction = model.predict_one(features.loc[learn_idx, FEATURES])
                if pd.notna(learn_label):
                    model.learn_one(features.loc[learn_idx, FEATURES], int(learn_label))

                signal_row = features.loc[signal_idx, FEATURES]
                river_prediction = model.predict_one(signal_row)
                self._save_model(symbol, model)

                regime = detect_regime(signal_row)
                batch_model = self._load_or_train_batch_model(
                    symbol,
                    features,
                    labels,
                    signal_idx,
                )
                batch_prediction = batch_model.predict_one(signal_row, regime)
                current_equity = state.equity()
                drawdown = 0.0 if state.peak_equity <= 0 else max(
                    0.0,
                    1.0 - current_equity / state.peak_equity,
                )
                drawdown_bucket = (
                    "high"
                    if drawdown >= 0.10
                    else "medium"
                    if drawdown >= 0.05
                    else "low"
                )
                volatility_bucket = (
                    "high"
                    if float(signal_row["vol_10"]) >= 0.02
                    else "normal"
                )
                context = MetaContext(
                    symbol=symbol,
                    regime=regime.name,
                    volatility_bucket=volatility_bucket,
                    drawdown_bucket=drawdown_bucket,
                )

                records = self.quality_store.load()
                quality_scores = {}
                for model_name in ("river", "ensemble"):
                    key = f"{symbol}:{model_name}"
                    if key in records:
                        record = records[key]
                        quality_scores[model_name] = evaluate_model_quality(
                            pd.Series(record.predictions),
                            pd.Series(record.confidences),
                            pd.Series(record.labels),
                        ).score
                    else:
                        quality_scores[model_name] = 0.50

                base_blend = blend_predictions(
                    [
                        BlendComponent("river", river_prediction, quality_scores["river"]),
                        BlendComponent("ensemble", batch_prediction, quality_scores["ensemble"]),
                    ]
                )
                routed = route_predictions(
                    {
                        "river": river_prediction,
                        "ensemble": batch_prediction,
                        "quality_blend": base_blend,
                    },
                    self.meta_store.scores(context),
                )
                blended = routed.prediction

                side = blended.side
                if blended.confidence < self.risk_config.min_confidence:
                    side = 0

                realized = labels.get(learn_idx)
                if pd.notna(realized):
                    realized_int = int(realized)
                    river_key = f"{symbol}:river"
                    self.quality_store.append(
                        river_key,
                        prediction=evaluation_prediction.side,
                        confidence=evaluation_prediction.confidence,
                        label=realized_int,
                    )

                    batch_eval_row = features.loc[learn_idx, FEATURES]
                    batch_eval_prediction = batch_model.predict_one(
                        batch_eval_row,
                        detect_regime(batch_eval_row),
                    )
                    ensemble_key = f"{symbol}:ensemble"
                    self.quality_store.append(
                        ensemble_key,
                        prediction=batch_eval_prediction.side,
                        confidence=batch_eval_prediction.confidence,
                        label=realized_int,
                    )

                    for model_name, evaluation in (
                        ("river", evaluation_prediction),
                        ("ensemble", batch_eval_prediction),
                    ):
                        correct = evaluation.side == realized_int
                        edge = (
                            1.0
                            if correct and evaluation.side != 0
                            else -1.0
                            if evaluation.side != 0
                            else 0.0
                        )
                        self.meta_store.update(
                            context,
                            model_name,
                            correct=correct,
                            edge=edge,
                        )

                signals[symbol] = side
                confidences[symbol] = blended.confidence
                signed_weights.loc[symbol] = base_weights.loc[symbol] * side

            annualized_volatility = returns.std(ddof=1) * (252 ** 0.5)
            expected_alpha = pd.Series(
                {
                    symbol: float(signals[symbol]) * max(0.0, confidences[symbol] - 0.5)
                    for symbol in signed_weights.index
                },
                dtype=float,
            )
            quality_scores = pd.Series(
                {
                    symbol: max(0.05, confidences[symbol])
                    for symbol in signed_weights.index
                },
                dtype=float,
            )
            alpha_weights = alpha_risk_weights(
                expected_alpha,
                annualized_volatility,
                quality_scores,
                self.alpha_allocation_config,
            )
            signed_weights = signed_weights * 0.5 + alpha_weights * 0.5

            equity = state.equity()
            previous_prices = {
                symbol: state.positions.get(symbol, AssetPosition()).last_price
                for symbol in signed_weights.index
            }
            previous_units = {
                symbol: state.positions.get(symbol, AssetPosition()).units
                for symbol in signed_weights.index
            }

            intelligent_weights, intelligence = apply_portfolio_intelligence(
                signed_weights,
                returns,
                confidences,
                current_equity=equity,
                peak_equity=state.peak_equity,
                config=self.intelligence_config,
            )
            notionals = target_notionals(equity, intelligent_weights)

            risk = evaluate_portfolio_risk(
                notionals,
                equity,
                returns,
                self.portfolio_risk_config,
            )

            if risk.approved:
                total_costs = 0.0
                for symbol in intelligent_weights.index:
                    price = float(opens[symbol].iloc[-1])
                    position = state.positions.setdefault(symbol, AssetPosition())
                    desired_units = float(notionals[symbol]) / price
                    delta_units = desired_units - position.units
                    gross = abs(delta_units) * price
                    bps = self.risk_config.transaction_cost_bps + self.risk_config.slippage_bps
                    total_costs += gross * bps / 10_000.0
                    state.cash -= delta_units * price
                    position.units = desired_units
                    position.last_price = float(closes[symbol].iloc[-1])

                state.cash -= total_costs

            for symbol in intelligent_weights.index:
                position = state.positions.setdefault(symbol, AssetPosition())
                position.last_price = float(closes[symbol].iloc[-1])

            current_prices = {
                symbol: float(closes[symbol].iloc[-1])
                for symbol in intelligent_weights.index
            }
            attribution = attribute_pnl(
                previous_prices,
                current_prices,
                previous_units,
                max(equity, 1e-12),
            )

            state.processed_bars += 1
            state.last_processed = execution_time
            current_equity = state.equity()
            state.peak_equity = max(state.peak_equity, current_equity)
            self.state_store.save(state)

            self.audit.append(
                "multiasset_runtime_step",
                {
                    "timestamp": execution_time,
                    "base_weights": base_weights.to_dict(),
                    "signed_weights": signed_weights.to_dict(),
                    "intelligent_weights": intelligent_weights.to_dict(),
                    "intelligence": {
                        "leverage": intelligence.leverage,
                        "estimated_annual_volatility": intelligence.estimated_annual_volatility,
                        "drawdown_scale": intelligence.drawdown_scale,
                        "stress_scale": intelligence.stress_scale,
                        "confidence_scale": intelligence.confidence_scale,
                        "stress_detected": intelligence.stress_detected,
                    },
                    "signals": signals,
                    "confidences": confidences,
                    "notionals": notionals.to_dict(),
                    "risk_approved": risk.approved,
                    "risk_reasons": list(risk.reasons),
                    "equity": current_equity,
                    "cash": state.cash,
                    "pnl_attribution": {
                        symbol: {
                            "pnl": item.pnl,
                            "return_contribution": item.return_contribution,
                        }
                        for symbol, item in attribution.items()
                    },
                },
            )

            return MultiAssetStepResult(
                processed=True,
                timestamp=execution_time,
                equity=current_equity,
                cash=state.cash,
                weights={k: float(v) for k, v in intelligent_weights.items()},
                notionals={k: float(v) for k, v in notionals.items()},
                signals=signals,
                confidences=confidences,
                risk_approved=risk.approved,
                risk_reasons=risk.reasons,
            )

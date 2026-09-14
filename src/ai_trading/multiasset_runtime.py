from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import joblib
import pandas as pd

from .allocation_state import AllocationStateStore
from .alpha_allocation import AlphaAllocationConfig, alpha_risk_weights
from .alpha_attribution import build_alpha_contribution
from .audit import AuditLog
from .config import ModelConfig, RiskConfig
from .economic_meta import economic_route_weight
from .economic_meta_store import EconomicMetaStore
from .ensemble import EnsembleDirectionModel
from .expert_lifecycle import evaluate_expert_lifecycle
from .expert_pool import ExpertPoolStore, compute_budget_weights
from .features import FEATURES, make_features, make_labels
from .global_allocator import GlobalAllocatorConfig, allocate_global_capital
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
from .specialist_experts import SpecialistDirectionModel


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
        economic_meta_store: EconomicMetaStore | None = None,
        expert_pool_store: ExpertPoolStore | None = None,
        specialist_model_root: str | Path = "artifacts/models/specialists",
        allocation_state_store: AllocationStateStore | None = None,
        global_allocator_config: GlobalAllocatorConfig | None = None,
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
        self.economic_meta_store = economic_meta_store or EconomicMetaStore()
        self.expert_pool_store = expert_pool_store or ExpertPoolStore()
        self.specialist_model_root = Path(specialist_model_root)
        self.allocation_state_store = allocation_state_store or AllocationStateStore()
        self.global_allocator_config = global_allocator_config or GlobalAllocatorConfig()


    def _specialist_path(self, symbol: str, kind: str) -> Path:
        safe = symbol.replace("/", "_").replace("=", "_").replace("^", "_")
        return self.specialist_model_root / f"{safe}_{kind}.joblib"

    def _load_or_train_specialist(
        self,
        symbol: str,
        kind: str,
        features: pd.DataFrame,
        labels: pd.Series,
        signal_idx,
    ) -> SpecialistDirectionModel:
        path = self._specialist_path(symbol, kind)
        if path.exists():
            return joblib.load(path)

        train_idx = features.index[features.index < signal_idx]
        train_idx = train_idx.intersection(labels.dropna().index)
        model = SpecialistDirectionModel(kind, random_state=42)
        model.fit(features.loc[train_idx], labels.loc[train_idx])
        path.parent.mkdir(parents=True, exist_ok=True)
        temp = path.with_suffix(".tmp")
        joblib.dump(model, temp)
        temp.replace(path)
        return model

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
            route_weights_by_symbol: dict[str, dict[str, float]] = {}
            regimes_by_symbol: dict[str, str] = {}
            opportunity_keys: list[str] = []
            opportunity_alpha: dict[str, float] = {}
            opportunity_quality: dict[str, float] = {}
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
                try:
                    batch_model = self._load_or_train_batch_model(
                        symbol,
                        features,
                        labels,
                        signal_idx,
                    )
                    batch_prediction = batch_model.predict_one(signal_row, regime)
                except ValueError:
                    batch_model = None
                    batch_prediction = None
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
                model_names = ["river"] + (["ensemble"] if batch_prediction is not None else [])
                for model_name in model_names:
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

                blend_components = [
                    BlendComponent("river", river_prediction, quality_scores["river"]),
                ]
                route_candidates = {"river": river_prediction}
                if batch_prediction is not None:
                    blend_components.append(
                        BlendComponent(
                            "ensemble",
                            batch_prediction,
                            quality_scores["ensemble"],
                        )
                    )
                    route_candidates["ensemble"] = batch_prediction

                base_blend = blend_predictions(blend_components)
                route_candidates["quality_blend"] = base_blend

                pool_records = self.expert_pool_store.load()
                pool_budget = compute_budget_weights(pool_records)
                for expert_name, budget in pool_budget.items():
                    record = pool_records[expert_name]
                    if not expert_name.startswith(f"{symbol}:"):
                        continue
                    if record.kind not in {"trend", "range", "high_vol"}:
                        continue
                    try:
                        specialist = self._load_or_train_specialist(
                            symbol,
                            record.kind,
                            features,
                            labels,
                            signal_idx,
                        )
                    except ValueError:
                        continue
                    if not specialist.supports(regime):
                        continue
                    specialist_prediction = specialist.predict_one(signal_row)
                    candidate_name = f"specialist_{record.kind}"
                    route_candidates[candidate_name] = specialist_prediction

                contextual_scores = self.meta_store.scores(context)
                for expert_name, budget in pool_budget.items():
                    if expert_name.startswith(f"{symbol}:"):
                        kind = pool_records[expert_name].kind
                        contextual_scores[f"specialist_{kind}"] = max(
                            contextual_scores.get(f"specialist_{kind}", 0.0),
                            float(budget),
                        )
                economic_stats = self.economic_meta_store.load()

                ensemble_economic_key = (
                    f"{symbol}|ensemble|{regime.name}|"
                    f"{volatility_bucket}|{drawdown_bucket}"
                )
                if "ensemble" in route_candidates and ensemble_economic_key in economic_stats:
                    lifecycle = evaluate_expert_lifecycle(
                        economic_stats[ensemble_economic_key]
                    )
                    if lifecycle.action == "retire":
                        route_candidates.pop("ensemble", None)
                    elif lifecycle.action == "retrain":
                        self._batch_model_path(symbol).unlink(missing_ok=True)

                for model_name in route_candidates:
                    economic_key = (
                        f"{symbol}|{model_name}|{regime.name}|"
                        f"{volatility_bucket}|{drawdown_bucket}"
                    )
                    if economic_key in economic_stats:
                        economic_weight = economic_route_weight(economic_stats[economic_key])
                        contextual_scores[model_name] = (
                            contextual_scores.get(model_name, 0.5) * economic_weight
                        )

                routed = route_predictions(
                    route_candidates,
                    contextual_scores,
                )
                blended = routed.prediction
                route_weights_by_symbol[symbol] = routed.weights
                regimes_by_symbol[symbol] = regime.name
                for model_name, model_weight in routed.weights.items():
                    opportunity_key = f"{symbol}|{model_name}|{regime.name}"
                    opportunity_keys.append(opportunity_key)
                    opportunity_alpha[opportunity_key] = float(blended.confidence) * float(blended.side) * float(model_weight)
                    opportunity_quality[opportunity_key] = float(model_weight)

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

                    evaluations = [("river", evaluation_prediction)]
                    if batch_model is not None:
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
                        evaluations.append(("ensemble", batch_eval_prediction))

                    for model_name, evaluation in evaluations:
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

            global_allocation_report = None
            if opportunity_keys:
                opportunity_returns = pd.DataFrame(index=returns.index)
                for key in opportunity_keys:
                    opportunity_symbol = key.split("|", 1)[0]
                    opportunity_returns[key] = returns[opportunity_symbol]

                global_allocation_report = allocate_global_capital(
                    opportunity_returns,
                    expected_alpha=pd.Series(opportunity_alpha, dtype=float),
                    quality=pd.Series(opportunity_quality, dtype=float),
                    current_weights=self.allocation_state_store.load(),
                    transaction_cost_bps=(
                        self.risk_config.transaction_cost_bps
                        + self.risk_config.slippage_bps
                    ),
                    config=self.global_allocator_config,
                )

                if global_allocation_report.approved:
                    asset_scale = pd.Series(
                        0.0,
                        index=intelligent_weights.index,
                        dtype=float,
                    )
                    for key, weight in global_allocation_report.weights.items():
                        opportunity_symbol = str(key).split("|", 1)[0]
                        if opportunity_symbol in asset_scale.index:
                            asset_scale.loc[opportunity_symbol] += abs(float(weight))

                    intelligent_weights = intelligent_weights * asset_scale
                    self.allocation_state_store.save(global_allocation_report.weights)
                else:
                    # Fail closed: rejected global allocation means no target
                    # risk until CVaR/turnover/cost constraints are satisfied.
                    intelligent_weights = intelligent_weights * 0.0

            notionals = target_notionals(equity, intelligent_weights)

            risk = evaluate_portfolio_risk(
                notionals,
                equity,
                returns,
                self.portfolio_risk_config,
            )

            total_costs = 0.0
            turnover_by_symbol = {symbol: 0.0 for symbol in intelligent_weights.index}
            costs_by_symbol = {symbol: 0.0 for symbol in intelligent_weights.index}

            if risk.approved:
                for symbol in intelligent_weights.index:
                    price = float(opens[symbol].iloc[-1])
                    position = state.positions.setdefault(symbol, AssetPosition())
                    desired_units = float(notionals[symbol]) / price
                    delta_units = desired_units - position.units
                    gross = abs(delta_units) * price
                    bps = self.risk_config.transaction_cost_bps + self.risk_config.slippage_bps
                    symbol_costs = gross * bps / 10_000.0
                    total_costs += symbol_costs
                    turnover_by_symbol[symbol] = gross
                    costs_by_symbol[symbol] = symbol_costs
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

            model_alpha_attribution = {}
            for symbol, item in attribution.items():
                model_alpha_attribution[symbol] = {}
                for model_name, model_weight in route_weights_by_symbol.get(symbol, {}).items():
                    contribution = build_alpha_contribution(
                        symbol=symbol,
                        model=model_name,
                        regime=regimes_by_symbol.get(symbol, "unknown"),
                        pnl=item.pnl * float(model_weight),
                        portfolio_equity=max(equity, 1e-12),
                    )
                    model_alpha_attribution[symbol][model_name] = {
                        "regime": contribution.regime,
                        "pnl": contribution.pnl,
                        "return_contribution": contribution.return_contribution,
                    }

            drawdown_now = (
                0.0
                if state.peak_equity <= 0
                else max(0.0, 1.0 - current_equity / state.peak_equity)
            )
            for symbol, models in model_alpha_attribution.items():
                for model_name, values in models.items():
                    economic_key = (
                        f"{symbol}|{model_name}|{values['regime']}|"
                        f"{'high' if float(features_by_symbol[symbol].loc[features_by_symbol[symbol].dropna().index[-2], 'vol_10']) >= 0.02 else 'normal'}|"
                        f"{'high' if drawdown_now >= 0.10 else 'medium' if drawdown_now >= 0.05 else 'low'}"
                    )
                    route_weight = route_weights_by_symbol.get(symbol, {}).get(model_name, 0.0)
                    self.economic_meta_store.update(
                        economic_key,
                        pnl=float(values["pnl"]),
                        turnover=float(turnover_by_symbol.get(symbol, 0.0)) * route_weight,
                        costs=float(costs_by_symbol.get(symbol, 0.0)) * route_weight,
                        drawdown=drawdown_now,
                        equity=max(equity, 1e-12),
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
                    "model_alpha_attribution": model_alpha_attribution,
                    "meta_route_weights": route_weights_by_symbol,
                    "regimes": regimes_by_symbol,
                    "global_allocation": (
                        {
                            "approved": global_allocation_report.approved,
                            "cvar": global_allocation_report.cvar,
                            "expected_return": global_allocation_report.expected_return,
                            "turnover": global_allocation_report.turnover,
                            "estimated_cost": global_allocation_report.estimated_cost,
                            "reasons": list(global_allocation_report.reasons),
                            "weights": global_allocation_report.weights.to_dict(),
                        }
                        if global_allocation_report is not None
                        else None
                    ),
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

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from .backtest import WalkForwardBacktester, WalkForwardConfig
from .champions import ChampionRegistry
from .config import ModelConfig, RiskConfig
from .ensemble import EnsembleDirectionModel
from .features import make_features, make_labels
from .performance import PerformanceMetrics
from .persistence import ModelStore
from .promotion import PromotionDecision, evaluate_challenger
from .regime_validation import RegimeValidation, validate_regime_returns
from .robustness import BootstrapReport, block_bootstrap_returns
from .tuning import TuningResult, tune_walk_forward


@dataclass(frozen=True)
class ContinuousCycleResult:
    tuning: TuningResult
    promotion: PromotionDecision
    regime_validation: RegimeValidation
    robustness: BootstrapReport
    promoted: bool
    champion_version: str | None


def run_learning_cycle(
    df: pd.DataFrame,
    *,
    symbol: str,
    champion_metrics: PerformanceMetrics,
    registry: ChampionRegistry,
    model_store: ModelStore | None = None,
    trials: int = 10,
) -> ContinuousCycleResult:
    tuning = tune_walk_forward(df, trials=trials, use_ensemble=True)

    risk = RiskConfig(
        min_confidence=float(tuning.best_params["min_confidence"]),
        max_position_fraction=float(tuning.best_params["max_position_fraction"]),
        max_daily_loss_fraction=float(tuning.best_params["max_daily_loss_fraction"]),
        max_drawdown_fraction=float(tuning.best_params["max_drawdown_fraction"]),
    )
    model_config = ModelConfig(
        horizon_bars=1,
        return_threshold=float(tuning.best_params["return_threshold"]),
    )
    wf = WalkForwardConfig(
        min_train_bars=252,
        test_window_bars=63,
        max_train_bars=int(tuning.best_params["max_train_bars"]),
        use_ensemble=True,
    )

    challenger = WalkForwardBacktester(
        risk_config=risk,
        model_config=model_config,
        config=wf,
    ).run(df)

    promotion = evaluate_challenger(champion_metrics, challenger.metrics)
    regime_validation = validate_regime_returns(challenger.regime_returns)
    robustness = block_bootstrap_returns(challenger.equity_curve)

    promoted = (
        promotion.promote
        and regime_validation.valid
        and robustness.probability_positive >= 0.60
        and robustness.p05_return > -0.15
    )

    version = None
    if promoted:
        version = f"{symbol}-ensemble-{len(registry.list()) + 1}"
        registry.promote(
            version=version,
            model_name="regime-aware-ensemble",
            score=tuning.best_score,
            metrics=challenger.metrics.as_dict(),
            config={
                "risk": risk.__dict__,
                "model": model_config.__dict__,
                "walk_forward": wf.as_dict(),
                "tuning": tuning.best_params,
            },
        )

        features = make_features(df)
        labels = make_labels(
            df,
            horizon_bars=model_config.horizon_bars,
            return_threshold=model_config.return_threshold,
        )
        final_model = EnsembleDirectionModel(random_state=42)
        final_model.fit(features, labels)

        store = model_store or ModelStore()
        store.save(
            version,
            final_model,
            {
                "symbol": symbol,
                "score": tuning.best_score,
                "metrics": challenger.metrics.as_dict(),
                "risk": risk.__dict__,
                "model": model_config.__dict__,
            },
        )

    return ContinuousCycleResult(
        tuning=tuning,
        promotion=promotion,
        regime_validation=regime_validation,
        robustness=robustness,
        promoted=promoted,
        champion_version=version,
    )

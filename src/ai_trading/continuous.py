from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from .backtest import WalkForwardBacktester, WalkForwardConfig
from .champions import ChampionRegistry
from .config import ModelConfig, RiskConfig
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
    champion_metrics,
    registry: ChampionRegistry,
    trials: int = 10,
) -> ContinuousCycleResult:
    tuning = tune_walk_forward(df, trials=trials, use_ensemble=True)

    risk = RiskConfig(
        min_confidence=float(tuning.best_params["min_confidence"]),
        max_position_fraction=float(tuning.best_params["max_position_fraction"]),
        max_daily_loss_fraction=float(tuning.best_params["max_daily_loss_fraction"]),
        max_drawdown_fraction=float(tuning.best_params["max_drawdown_fraction"]),
    )
    model = ModelConfig(
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
        model_config=model,
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
                "model": model.__dict__,
                "walk_forward": wf.as_dict(),
                "tuning": tuning.best_params,
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

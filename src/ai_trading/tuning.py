from __future__ import annotations

from dataclasses import dataclass

import optuna
import pandas as pd

from .backtest import WalkForwardBacktester, WalkForwardConfig
from .config import ModelConfig, RiskConfig
from .performance import PerformanceMetrics


@dataclass(frozen=True)
class OptimizationWeights:
    return_weight: float = 1.0
    sharpe_weight: float = 0.35
    sortino_weight: float = 0.15
    drawdown_penalty: float = 1.25


@dataclass(frozen=True)
class TuningResult:
    best_score: float
    best_params: dict[str, float]
    trials: int


def objective_score(
    metrics: PerformanceMetrics,
    weights: OptimizationWeights | None = None,
) -> float:
    """Risk-aware scalar objective for hyperparameter searches."""
    weights = weights or OptimizationWeights()
    return float(
        weights.return_weight * metrics.total_return
        + weights.sharpe_weight * metrics.sharpe
        + weights.sortino_weight * metrics.sortino
        - weights.drawdown_penalty * metrics.max_drawdown
    )


def tune_walk_forward(
    df: pd.DataFrame,
    *,
    trials: int = 20,
    use_ensemble: bool = True,
    random_state: int = 42,
) -> TuningResult:
    if trials < 1:
        raise ValueError("trials must be positive")

    sampler = optuna.samplers.TPESampler(seed=random_state)
    study = optuna.create_study(direction="maximize", sampler=sampler)

    def objective(trial: optuna.Trial) -> float:
        risk = RiskConfig(
            min_confidence=trial.suggest_float("min_confidence", 0.50, 0.75),
            max_position_fraction=trial.suggest_float("max_position_fraction", 0.02, 0.15),
            max_daily_loss_fraction=trial.suggest_float("max_daily_loss_fraction", 0.01, 0.03),
            max_drawdown_fraction=trial.suggest_float("max_drawdown_fraction", 0.05, 0.15),
            transaction_cost_bps=2.0,
            slippage_bps=1.0,
        )
        model = ModelConfig(
            horizon_bars=1,
            return_threshold=trial.suggest_float("return_threshold", 0.0005, 0.0030),
        )
        wf = WalkForwardConfig(
            min_train_bars=252,
            test_window_bars=63,
            max_train_bars=trial.suggest_int("max_train_bars", 504, 1260, step=126),
            use_ensemble=use_ensemble,
        )
        report = WalkForwardBacktester(
            risk_config=risk,
            model_config=model,
            config=wf,
        ).run(df)

        if report.metrics.max_drawdown > risk.max_drawdown_fraction + 1e-9:
            return -1e9
        return objective_score(report.metrics)

    study.optimize(objective, n_trials=trials, show_progress_bar=False)

    return TuningResult(
        best_score=float(study.best_value),
        best_params={k: float(v) for k, v in study.best_params.items()},
        trials=len(study.trials),
    )

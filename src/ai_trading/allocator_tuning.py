from __future__ import annotations

from dataclasses import dataclass

import optuna
import pandas as pd

from .global_allocator import GlobalAllocatorConfig, allocate_global_capital
from .performance import compute_metrics


@dataclass(frozen=True)
class AllocatorTuningResult:
    best_score: float
    best_config: GlobalAllocatorConfig
    trials: int


def _fold_score(
    train: pd.DataFrame,
    test: pd.DataFrame,
    config: GlobalAllocatorConfig,
) -> float:
    expected_alpha = train.mean()
    quality = (1.0 / train.std(ddof=1).replace(0.0, pd.NA)).fillna(0.0)
    if float(quality.sum()) > 0:
        quality = quality / quality.max()

    report = allocate_global_capital(
        train,
        expected_alpha=expected_alpha,
        quality=quality,
        current_weights=pd.Series(0.0, index=train.columns, dtype=float),
        config=config,
    )
    if not report.approved:
        return -10.0

    returns = test.fillna(0.0).mul(report.weights, axis=1).sum(axis=1)
    equity = (1.0 + returns).cumprod() * 100_000.0
    metrics = compute_metrics(equity)

    return float(
        metrics.total_return
        + 0.35 * metrics.sharpe
        + 0.15 * metrics.sortino
        - 1.25 * metrics.max_drawdown
        - 0.50 * report.cvar
        - 0.10 * report.turnover
    )


def tune_global_allocator(
    opportunity_returns: pd.DataFrame,
    *,
    trials: int = 25,
    folds: int = 3,
    random_state: int = 42,
) -> AllocatorTuningResult:
    clean = opportunity_returns.astype(float).dropna()
    if len(clean) < 180:
        raise ValueError("Need at least 180 aligned observations to tune allocator")
    if folds < 2:
        raise ValueError("folds must be at least 2")

    fold_size = len(clean) // (folds + 1)
    if fold_size < 40:
        raise ValueError("Insufficient observations per temporal fold")

    study = optuna.create_study(
        direction="maximize",
        sampler=optuna.samplers.TPESampler(seed=random_state),
    )

    def objective(trial: optuna.Trial) -> float:
        config = GlobalAllocatorConfig(
            cvar_alpha=trial.suggest_float("cvar_alpha", 0.90, 0.99),
            max_cvar=trial.suggest_float("max_cvar", 0.01, 0.08),
            max_asset_weight=trial.suggest_float("max_asset_weight", 0.25, 0.60),
            max_expert_weight=trial.suggest_float("max_expert_weight", 0.10, 0.40),
            max_turnover=trial.suggest_float("max_turnover", 0.20, 1.50),
            target_gross_exposure=trial.suggest_float("target_gross_exposure", 0.40, 1.00),
            cost_penalty=trial.suggest_float("cost_penalty", 0.5, 2.0),
            turnover_penalty=trial.suggest_float("turnover_penalty", 0.05, 0.50),
        )

        scores: list[float] = []
        for fold in range(folds):
            train_end = fold_size * (fold + 1)
            test_end = train_end + fold_size
            train = clean.iloc[:train_end]
            test = clean.iloc[train_end:test_end]
            if len(test) < 20:
                continue
            scores.append(_fold_score(train, test, config))

        if not scores:
            return -10.0
        return float(sum(scores) / len(scores))

    study.optimize(objective, n_trials=trials, show_progress_bar=False)

    p = study.best_params
    best = GlobalAllocatorConfig(
        cvar_alpha=float(p["cvar_alpha"]),
        max_cvar=float(p["max_cvar"]),
        max_asset_weight=float(p["max_asset_weight"]),
        max_expert_weight=float(p["max_expert_weight"]),
        max_turnover=float(p["max_turnover"]),
        target_gross_exposure=float(p["target_gross_exposure"]),
        cost_penalty=float(p["cost_penalty"]),
        turnover_penalty=float(p["turnover_penalty"]),
    )
    return AllocatorTuningResult(
        best_score=float(study.best_value),
        best_config=best,
        trials=len(study.trials),
    )

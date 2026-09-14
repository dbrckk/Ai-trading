from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from .features import make_features, make_labels
from .performance import PerformanceMetrics, compute_metrics
from .purged_cv import purged_expanding_folds
from .specialist_experts import SpecialistDirectionModel


@dataclass(frozen=True)
class FoldResult:
    metrics: PerformanceMetrics
    accuracy: float
    observations: int


@dataclass(frozen=True)
class TemporalCVReport:
    folds: tuple[FoldResult, ...]
    mean_accuracy: float
    mean_sharpe: float
    worst_drawdown: float
    aggregate_score: float


def temporal_cross_validate_specialist(
    df: pd.DataFrame,
    *,
    kind: str,
    return_threshold: float,
    horizon_bars: int = 1,
    folds: int = 3,
    min_train_bars: int = 120,
    test_bars: int = 40,
    purge_bars: int = 5,
    embargo_bars: int = 5,
) -> TemporalCVReport:
    features = make_features(df)
    labels = make_labels(
        df,
        horizon_bars=horizon_bars,
        return_threshold=return_threshold,
    )
    usable = features.dropna().index.intersection(labels.dropna().index)

    split_folds = purged_expanding_folds(
        usable,
        folds=folds,
        min_train_bars=min_train_bars,
        test_bars=test_bars,
        purge_bars=purge_bars,
        embargo_bars=embargo_bars,
    )

    results: list[FoldResult] = []
    for fold_number, split in enumerate(split_folds):
        train_idx = split.train_index
        test_idx = split.test_index

        model = SpecialistDirectionModel(kind, random_state=42 + fold_number)
        model.fit(features.loc[train_idx], labels.loc[train_idx])

        equity = [100_000.0]
        correct = 0
        observations = 0

        for idx in test_idx[:-1]:
            pred = model.predict_one(features.loc[idx])
            label = int(labels.loc[idx])
            correct += int(pred.side == label)
            observations += 1

            pos = int(df.index.get_loc(idx))
            if pos + 1 >= len(df.index):
                continue
            next_idx = df.index[pos + 1]
            ret = float(df.at[next_idx, "Close"] / df.at[next_idx, "Open"] - 1.0)
            equity.append(equity[-1] * (1.0 + pred.side * ret))

        metrics = compute_metrics(pd.Series(equity, dtype=float))
        results.append(
            FoldResult(
                metrics=metrics,
                accuracy=correct / max(1, observations),
                observations=observations,
            )
        )

    if not results:
        raise ValueError("Temporal CV produced no folds")

    mean_accuracy = sum(r.accuracy for r in results) / len(results)
    mean_sharpe = sum(r.metrics.sharpe for r in results) / len(results)
    worst_drawdown = max(r.metrics.max_drawdown for r in results)
    aggregate_score = (
        0.35 * mean_accuracy
        + 0.40 * max(0.0, min(1.0, (mean_sharpe + 1.0) / 3.0))
        + 0.25 * max(0.0, 1.0 - worst_drawdown)
    )

    return TemporalCVReport(
        folds=tuple(results),
        mean_accuracy=float(mean_accuracy),
        mean_sharpe=float(mean_sharpe),
        worst_drawdown=float(worst_drawdown),
        aggregate_score=float(max(0.0, min(1.0, aggregate_score))),
    )

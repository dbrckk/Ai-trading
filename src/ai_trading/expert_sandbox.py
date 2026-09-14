from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from .features import make_features, make_labels
from .performance import PerformanceMetrics, compute_metrics
from .specialist_experts import SpecialistDirectionModel


@dataclass(frozen=True)
class SandboxResult:
    metrics: PerformanceMetrics
    accuracy: float
    validation_score: float
    observations: int


def validate_specialist(
    df: pd.DataFrame,
    *,
    kind: str,
    train_fraction: float = 0.70,
    return_threshold: float = 0.001,
    horizon_bars: int = 1,
) -> SandboxResult:
    features = make_features(df)
    labels = make_labels(
        df,
        horizon_bars=horizon_bars,
        return_threshold=return_threshold,
    )
    usable = features.dropna().index.intersection(labels.dropna().index)

    if len(usable) < 120:
        raise ValueError("Need at least 120 usable bars for specialist sandbox")

    split = max(80, int(len(usable) * train_fraction))
    train_idx = usable[:split]
    test_idx = usable[split:]
    if len(test_idx) < 20:
        raise ValueError("Need at least 20 validation bars")

    model = SpecialistDirectionModel(kind)
    model.fit(features.loc[train_idx], labels.loc[train_idx])

    equity = [100_000.0]
    correct = 0
    active = 0

    for idx in test_idx[:-1]:
        pred = model.predict_one(features.loc[idx])
        label = int(labels.loc[idx])
        if pred.side == label:
            correct += 1
        if pred.side != 0:
            active += 1

        current_pos = int(df.index.get_loc(idx))
        next_idx = df.index[current_pos + 1]
        ret = float(df.at[next_idx, "Close"] / df.at[next_idx, "Open"] - 1.0)
        equity.append(equity[-1] * (1.0 + pred.side * ret))

    curve = pd.Series(equity, dtype=float)
    metrics = compute_metrics(curve)
    observations = max(1, len(test_idx) - 1)
    accuracy = correct / observations
    validation_score = max(
        0.0,
        min(
            1.0,
            0.45 * accuracy
            + 0.35 * max(0.0, min(1.0, (metrics.sharpe + 1.0) / 3.0))
            + 0.20 * max(0.0, 1.0 - metrics.max_drawdown),
        ),
    )
    return SandboxResult(
        metrics=metrics,
        accuracy=accuracy,
        validation_score=float(validation_score),
        observations=observations,
    )

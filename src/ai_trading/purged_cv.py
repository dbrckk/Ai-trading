from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class PurgedFold:
    train_index: pd.Index
    test_index: pd.Index


def purged_expanding_folds(
    index: pd.Index,
    *,
    folds: int = 3,
    min_train_bars: int = 120,
    test_bars: int = 40,
    purge_bars: int = 5,
    embargo_bars: int = 5,
) -> tuple[PurgedFold, ...]:
    if folds < 1:
        raise ValueError("folds must be at least 1")
    if min_train_bars < 1 or test_bars < 1:
        raise ValueError("train and test sizes must be positive")
    if purge_bars < 0 or embargo_bars < 0:
        raise ValueError("purge and embargo must be non-negative")

    required = (
        min_train_bars
        + purge_bars
        + folds * test_bars
        + max(0, folds - 1) * embargo_bars
    )
    if len(index) < required:
        raise ValueError(f"need at least {required} observations")

    result: list[PurgedFold] = []
    cursor = min_train_bars

    for _ in range(folds):
        train_end = max(0, cursor - purge_bars)
        test_start = cursor
        test_end = test_start + test_bars

        train_index = index[:train_end]
        test_index = index[test_start:test_end]

        if len(train_index) < min_train_bars - purge_bars:
            raise ValueError("purge leaves insufficient training history")
        if len(test_index) != test_bars:
            raise ValueError("insufficient test observations")

        result.append(
            PurgedFold(
                train_index=train_index,
                test_index=test_index,
            )
        )
        cursor = test_end + embargo_bars

    return tuple(result)

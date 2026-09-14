import pandas as pd

from ai_trading.purged_cv import purged_expanding_folds


def test_purged_cv_separates_train_and_test() -> None:
    index = pd.RangeIndex(0, 400)
    folds = purged_expanding_folds(
        index,
        folds=3,
        min_train_bars=120,
        test_bars=40,
        purge_bars=5,
        embargo_bars=5,
    )

    assert len(folds) == 3
    for fold in folds:
        assert max(fold.train_index) <= min(fold.test_index) - 6
        assert set(fold.train_index).isdisjoint(set(fold.test_index))


def test_purged_cv_embargo_moves_next_test_forward() -> None:
    index = pd.RangeIndex(0, 400)
    folds = purged_expanding_folds(
        index,
        folds=2,
        min_train_bars=120,
        test_bars=40,
        purge_bars=5,
        embargo_bars=7,
    )
    assert min(folds[1].test_index) == max(folds[0].test_index) + 8

import numpy as np
import pandas as pd

from ai_trading.features import FEATURES, make_features, make_labels


def sample_df(n: int = 100) -> pd.DataFrame:
    idx = pd.date_range("2025-01-01", periods=n, freq="D")
    close = pd.Series(100 + np.linspace(0, 20, n) + np.sin(np.arange(n)), index=idx)
    return pd.DataFrame(
        {
            "Open": close * 0.999,
            "High": close * 1.01,
            "Low": close * 0.99,
            "Close": close,
            "Volume": 1000 + np.arange(n),
        },
        index=idx,
    )


def test_features_have_expected_columns() -> None:
    x = make_features(sample_df())
    assert list(x.columns) == FEATURES
    assert x.dropna().shape[0] > 0


def test_labels_only_three_classes() -> None:
    y = make_labels(sample_df(), return_threshold=0.002).dropna().astype(int)
    assert set(y.unique()).issubset({-1, 0, 1})

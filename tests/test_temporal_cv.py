import numpy as np
import pandas as pd

from ai_trading.temporal_cv import temporal_cross_validate_specialist


def market(n: int = 320) -> pd.DataFrame:
    idx = pd.date_range("2023-01-01", periods=n, freq="D")
    t = np.arange(n, dtype=float)
    close = 100 + 0.04 * t + 4.0 * np.sin(t / 9.0)
    open_ = close * (1.0 + 0.001 * np.sin(t / 4.0))
    return pd.DataFrame(
        {
            "Open": open_,
            "High": np.maximum(open_, close) * 1.005,
            "Low": np.minimum(open_, close) * 0.995,
            "Close": close,
            "Volume": 1000.0 + t,
        },
        index=idx,
    )


def test_temporal_cv_produces_multiple_folds() -> None:
    report = temporal_cross_validate_specialist(
        market(),
        kind="trend",
        return_threshold=0.001,
        folds=3,
        min_train_bars=120,
        test_bars=40,
    )
    assert len(report.folds) == 3
    assert 0.0 <= report.aggregate_score <= 1.0
    assert report.worst_drawdown >= 0.0

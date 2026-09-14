import numpy as np
import pandas as pd

from ai_trading.backtest import WalkForwardBacktester, WalkForwardConfig
from ai_trading.config import ModelConfig, RiskConfig


def sample_market(n: int = 420) -> pd.DataFrame:
    idx = pd.date_range("2020-01-01", periods=n, freq="D")
    t = np.arange(n, dtype=float)
    close = 100.0 + 0.05 * t + 5.0 * np.sin(t / 8.0) + 2.0 * np.sin(t / 2.7)
    open_ = close * (1.0 + 0.0015 * np.sin(t / 4.0))
    return pd.DataFrame(
        {
            "Open": open_,
            "High": np.maximum(open_, close) * 1.006,
            "Low": np.minimum(open_, close) * 0.994,
            "Close": close,
            "Volume": 1500.0 + t + 120.0 * np.sin(t / 10.0),
        },
        index=idx,
    )


def test_walk_forward_ensemble_runs() -> None:
    report = WalkForwardBacktester(
        risk_config=RiskConfig(min_confidence=0.0),
        model_config=ModelConfig(return_threshold=0.001),
        config=WalkForwardConfig(
            min_train_bars=140,
            test_window_bars=40,
            max_train_bars=220,
            use_ensemble=True,
        ),
    ).run(sample_market())

    assert report.folds >= 2
    assert report.decisions > 0
    assert len(report.equity_curve) == report.decisions

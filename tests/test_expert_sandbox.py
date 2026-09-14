import numpy as np
import pandas as pd

from ai_trading.expert_sandbox import validate_specialist


def market(n: int = 220) -> pd.DataFrame:
    idx = pd.date_range("2024-01-01", periods=n, freq="D")
    t = np.arange(n, dtype=float)
    close = 100 + 0.05 * t + 3.0 * np.sin(t / 8.0)
    open_ = close * (1.0 + 0.001 * np.sin(t / 3.0))
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


def test_specialist_sandbox_returns_validation_score() -> None:
    result = validate_specialist(market(), kind="trend", train_fraction=0.65)
    assert 0.0 <= result.validation_score <= 1.0
    assert 0.0 <= result.accuracy <= 1.0
    assert result.observations >= 20

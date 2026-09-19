import numpy as np
import pandas as pd

from ai_trading.ensemble import EnsembleDirectionModel
from ai_trading.features import FEATURES
from ai_trading.regime import MarketRegime


def sample_training(n: int = 180) -> tuple[pd.DataFrame, pd.Series]:
    t = np.arange(n, dtype=float)
    x = pd.DataFrame(
        {
            "ret_1": np.sin(t / 5.0) * 0.01,
            "ret_5": np.sin(t / 8.0) * 0.02,
            "vol_10": 0.01 + (np.cos(t / 9.0) + 1.0) * 0.005,
            "trend_10": np.sin(t / 17.0) * 0.03,
            "trend_30": np.sin(t / 29.0) * 0.02,
            "range_pct": 0.01 + (np.sin(t / 13.0) + 1.0) * 0.002,
            "volume_z20": np.sin(t / 7.0),
        }
    )
    y = pd.Series(np.where(x["trend_10"] > 0.008, 1, np.where(x["trend_10"] < -0.008, -1, 0)))
    return x, y


def test_ensemble_returns_valid_probability_distribution() -> None:
    x, y = sample_training()
    model = EnsembleDirectionModel(random_state=7)
    model.fit(x, y)
    pred = model.predict_one(
        x.loc[150, FEATURES],
        MarketRegime("bull", "normal_vol"),
    )
    assert pred.side in {-1, 0, 1}
    assert 0.0 <= pred.confidence <= 1.0
    assert abs(sum(pred.probabilities.values()) - 1.0) < 1e-6



def test_ensemble_accepts_explicit_feature_set() -> None:
    x, y = sample_training()
    x = x.copy()
    x["extra_momentum"] = np.cos(np.arange(len(x), dtype=float) / 11.0)
    feature_names = [*FEATURES, "extra_momentum"]

    model = EnsembleDirectionModel(random_state=11, feature_names=feature_names)
    model.fit(x, y)
    pred = model.predict_one(
        x.loc[150, feature_names],
        MarketRegime("sideways", "normal_vol"),
    )

    assert pred.side in {-1, 0, 1}
    assert abs(sum(pred.probabilities.values()) - 1.0) < 1e-6

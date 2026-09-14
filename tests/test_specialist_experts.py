import numpy as np
import pandas as pd

from ai_trading.features import FEATURES
from ai_trading.specialist_experts import SpecialistDirectionModel


def training_data(n: int = 140) -> tuple[pd.DataFrame, pd.Series]:
    t = np.arange(n, dtype=float)
    x = pd.DataFrame(
        {
            "ret_1": np.sin(t / 5.0) * 0.01,
            "ret_5": np.sin(t / 9.0) * 0.02,
            "vol_10": 0.01 + (np.cos(t / 11.0) + 1.0) * 0.005,
            "trend_10": np.sin(t / 17.0) * 0.03,
            "trend_30": np.sin(t / 29.0) * 0.02,
            "range_pct": 0.01 + (np.sin(t / 13.0) + 1.0) * 0.002,
            "volume_z20": np.sin(t / 7.0),
        }
    )
    y = pd.Series(np.where(x["trend_10"] > 0.006, 1, np.where(x["trend_10"] < -0.006, -1, 0)))
    return x, y


def test_all_specialist_kinds_train_and_predict() -> None:
    x, y = training_data()
    for kind in ("trend", "range", "high_vol"):
        model = SpecialistDirectionModel(kind)
        model.fit(x, y)
        pred = model.predict_one(x.loc[120, FEATURES])
        assert pred.side in {-1, 0, 1}
        assert abs(sum(pred.probabilities.values()) - 1.0) < 1e-6

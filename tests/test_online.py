import numpy as np
import pandas as pd

from ai_trading.features import FEATURES
from ai_trading.online import RiverDirectionModel


def row(value: float) -> pd.Series:
    return pd.Series({name: value for name in FEATURES})


def test_river_model_learns_incrementally() -> None:
    model = RiverDirectionModel()
    for value in np.linspace(-1.0, 1.0, 120):
        label = 1 if value > 0.2 else (-1 if value < -0.2 else 0)
        model.learn_one(row(float(value)), label)

    prediction = model.predict_one(row(0.9))
    assert prediction.side in {-1, 0, 1}
    assert 0.0 <= prediction.confidence <= 1.0
    assert model.stats.observations == 120

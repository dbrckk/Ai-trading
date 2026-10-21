import numpy as np
import pandas as pd

from ai_trading.features import FEATURES
from ai_trading.online import RiverDirectionModel, RiverMulticlassDirectionModel


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


def test_research_river_multiclass_learns_all_three_directions() -> None:
    model = RiverMulticlassDirectionModel()
    for _ in range(6):
        for value in np.linspace(-3.0, 3.0, 90):
            label = -1 if value < -0.7 else (1 if value > 0.7 else 0)
            model.learn_one(row(float(value)), label)

    short = model.predict_one(row(-2.0))
    long = model.predict_one(row(2.0))
    assert model.stats.observations == 540
    assert set(short.probabilities) == {-1, 0, 1}
    assert 0.0 < short.probabilities[-1] <= 1.0
    assert short.side == -1
    assert long.side == 1
    assert abs(sum(short.probabilities.values()) - 1.0) < 1e-9

    # The research state survives a v2-only round trip after actual learning.
    from ai_trading.research_model_codec import (
        deserialize_research_model,
        serialize_research_model,
    )

    restored = deserialize_research_model(serialize_research_model(model))
    assert restored.stats.observations == 540
    assert restored.predict_one(row(-2.0)).side == short.side
    assert restored.predict_one(row(2.0)).side == long.side


def test_legacy_river_binary_probabilities_do_not_include_short() -> None:
    # Document existing v1 limitation without silently changing stored models.
    model = RiverDirectionModel()
    for value in np.linspace(-1.0, 1.0, 120):
        label = -1 if value < -0.2 else (1 if value > 0.2 else 0)
        model.learn_one(row(float(value)), label)

    negative = model.predict_one(row(-0.9))
    assert negative.probabilities[-1] == 0.0

import pandas as pd

from ai_trading.model_quality import evaluate_model_quality


def test_model_quality_rewards_better_predictions() -> None:
    labels = pd.Series([1, 1, -1, 0, 1, -1, 1, 0, -1, 1])
    good = evaluate_model_quality(
        pd.Series([1, 1, -1, 0, 1, -1, 1, 0, -1, 1]),
        pd.Series([0.9] * 10),
        labels,
    )
    bad = evaluate_model_quality(
        pd.Series([-1, 0, 1, 1, -1, 1, -1, 1, 1, -1]),
        pd.Series([0.9] * 10),
        labels,
    )
    assert good.score > bad.score
    assert good.accuracy > bad.accuracy

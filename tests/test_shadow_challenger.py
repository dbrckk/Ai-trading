from __future__ import annotations

import numpy as np
import pandas as pd

import ai_trading.shadow_challenger as shadow_module
from ai_trading.features import FEATURES, make_features, make_labels
from ai_trading.model import Prediction
from ai_trading.shadow_challenger import evaluate_shadow_challenger


def sample_market(n: int = 220) -> pd.DataFrame:
    idx = pd.date_range("2025-01-01", periods=n, freq="5min")
    t = np.arange(n, dtype=float)
    close = 100.0 + 0.03 * t + 1.5 * np.sin(t / 7.0)
    open_ = close * (1.0 + 0.0005 * np.sin(t / 4.0))
    return pd.DataFrame(
        {
            "Open": open_,
            "High": np.maximum(open_, close) * 1.003,
            "Low": np.minimum(open_, close) * 0.997,
            "Close": close,
            "Volume": 1000.0 + 2.0 * t,
        },
        index=idx,
    )


def test_shadow_challenger_purges_unobservable_training_labels(monkeypatch) -> None:
    market = sample_market()
    features = make_features(market)
    labels = make_labels(market, horizon_bars=3, return_threshold=0.001)
    execution_idx = market.index[-2]
    captured: dict[str, object] = {}

    class RecordingEnsemble:
        def __init__(self, random_state: int = 42) -> None:
            captured["random_state"] = random_state

        def fit(self, x: pd.DataFrame, y: pd.Series) -> None:
            captured["train_index"] = x.index
            assert x.index.equals(y.index)
            assert list(x.columns) == FEATURES

        def predict_one(self, row: pd.Series, regime) -> Prediction:
            captured["regime"] = regime.name
            return Prediction(
                side=0,
                confidence=0.70,
                probabilities={-1: 0.10, 0: 0.70, 1: 0.20},
            )

    monkeypatch.setattr(shadow_module, "EnsembleDirectionModel", RecordingEnsemble)

    result = evaluate_shadow_challenger(
        market,
        features,
        labels,
        execution_idx,
        horizon_bars=3,
        min_train_rows=100,
    )

    assert result is not None
    signal_pos = int(market.index.get_loc(execution_idx)) - 1
    train_index = captured["train_index"]
    assert isinstance(train_index, pd.Index)
    assert market.index.get_loc(train_index[-1]) <= signal_pos - 3
    assert result.training_end == str(train_index[-1])
    assert result.training_rows == len(train_index)
    assert result.execution_time == str(execution_idx)
    assert result.signal_time == str(market.index[signal_pos])
    assert result.regime == captured["regime"]
    expected_label = labels.loc[market.index[signal_pos]]
    assert result.realized_label == int(expected_label)


def test_shadow_challenger_skips_when_history_is_insufficient() -> None:
    market = sample_market(90)
    features = make_features(market)
    labels = make_labels(market)

    result = evaluate_shadow_challenger(
        market,
        features,
        labels,
        market.index[-2],
        min_train_rows=100,
    )

    assert result is None

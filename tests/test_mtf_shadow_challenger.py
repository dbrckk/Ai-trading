from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

import ai_trading.mtf_shadow_challenger as mtf_module
from ai_trading.features import make_features
from ai_trading.model import Prediction
from ai_trading.mtf_shadow_challenger import (
    evaluate_multi_timeframe_shadow,
    select_observable_execution_target,
)
from ai_trading.multi_timeframe_features import MTF_CHALLENGER_FEATURES


def sample_market(n: int = 2600) -> pd.DataFrame:
    idx = pd.date_range("2026-01-01", periods=n, freq="5min")
    t = np.arange(n, dtype=float)
    close = 100.0 + 0.015 * t + 1.3 * np.sin(t / 17.0)
    open_ = close * (1.0 + 0.0004 * np.sin(t / 9.0))
    return pd.DataFrame(
        {
            "Open": open_,
            "High": np.maximum(open_, close) * 1.0025,
            "Low": np.minimum(open_, close) * 0.9975,
            "Close": close,
            "Volume": 1000.0 + (t % 100) * 3.0,
        },
        index=idx,
    )


def test_select_observable_execution_target_delays_three_bar_horizon() -> None:
    market = sample_market(200)
    eligible = tuple(market.index[40:])
    current = eligible[-1]

    target = select_observable_execution_target(
        market,
        eligible,
        current,
        horizon_bars=3,
    )

    assert target == market.index[-3]


def test_mtf_shadow_purges_future_labels_and_caps_training(monkeypatch) -> None:
    market = sample_market()
    authoritative = make_features(market)
    execution_idx = market.index[-4]
    captured: dict[str, object] = {}
    original_feature_builder = mtf_module.make_multi_timeframe_challenger_features

    def recording_feature_builder(frame: pd.DataFrame) -> pd.DataFrame:
        captured["feature_rows"] = len(frame)
        return original_feature_builder(frame)

    monkeypatch.setattr(
        mtf_module,
        "make_multi_timeframe_challenger_features",
        recording_feature_builder,
    )

    class RecordingEnsemble:
        def __init__(
            self,
            random_state: int = 42,
            feature_names: tuple[str, ...] | list[str] | None = None,
        ) -> None:
            captured["random_state"] = random_state
            captured["feature_names"] = tuple(feature_names or ())

        def fit(self, x: pd.DataFrame, y: pd.Series) -> None:
            captured["train_index"] = x.index
            assert x.index.equals(y.index)
            assert list(x.columns) == MTF_CHALLENGER_FEATURES

        def predict_one(self, row: pd.Series, regime) -> Prediction:
            captured["regime"] = regime.name
            return Prediction(
                side=1,
                confidence=0.71,
                probabilities={-1: 0.12, 0: 0.17, 1: 0.71},
            )

    monkeypatch.setattr(mtf_module, "EnsembleDirectionModel", RecordingEnsemble)

    result = evaluate_multi_timeframe_shadow(
        market,
        authoritative,
        execution_idx,
        horizon_bars=3,
        min_train_rows=500,
        max_train_rows=700,
        feature_warmup_rows=400,
        minimum_threshold=0.001,
        atr_multiplier=0.25,
        min_confidence=0.60,
        config_name="test-h15",
    )

    assert result is not None
    assert captured["feature_names"] == tuple(MTF_CHALLENGER_FEATURES)
    train_index = captured["train_index"]
    assert isinstance(train_index, pd.Index)
    assert len(train_index) <= 700
    assert int(captured["feature_rows"]) <= 1103
    signal_pos = int(market.index.get_loc(execution_idx)) - 1
    assert market.index.get_loc(train_index[-1]) <= signal_pos - 3
    assert result.horizon_bars == 3
    assert result.horizon_minutes == 15
    assert result.timeframes == ("5m", "15m", "1h", "4h")
    assert result.feature_count == len(MTF_CHALLENGER_FEATURES)
    assert result.threshold_at_signal >= 0.001
    assert result.realized_label in {-1, 0, 1}
    assert result.regime == captured["regime"]
    assert result.config_name == "test-h15"
    assert result.raw_side == 1
    assert result.min_confidence == 0.60
    assert result.prediction.side == 1



def test_mtf_shadow_rejects_invalid_feature_warmup() -> None:
    market = sample_market(800)
    authoritative = make_features(market)

    with pytest.raises(ValueError, match="feature_warmup_rows"):
        evaluate_multi_timeframe_shadow(
            market,
            authoritative,
            market.index[-4],
            min_train_rows=100,
            max_train_rows=200,
            feature_warmup_rows=0,
        )



def test_mtf_shadow_confidence_gate_turns_weak_direction_flat(monkeypatch) -> None:
    market = sample_market()
    authoritative = make_features(market)
    execution_idx = market.index[-4]

    class WeakDirectionalEnsemble:
        def __init__(self, **kwargs) -> None:
            del kwargs

        def fit(self, x: pd.DataFrame, y: pd.Series) -> None:
            assert len(x) == len(y)

        def predict_one(self, row: pd.Series, regime) -> Prediction:
            del row, regime
            return Prediction(
                side=1,
                confidence=0.55,
                probabilities={-1: 0.15, 0: 0.30, 1: 0.55},
            )

    monkeypatch.setattr(
        mtf_module,
        "EnsembleDirectionModel",
        WeakDirectionalEnsemble,
    )

    result = evaluate_multi_timeframe_shadow(
        market,
        authoritative,
        execution_idx,
        horizon_bars=3,
        min_train_rows=500,
        max_train_rows=700,
        minimum_threshold=0.001,
        atr_multiplier=0.25,
        min_confidence=0.60,
        config_name="weak-direction",
    )

    assert result is not None
    assert result.raw_side == 1
    assert result.prediction.side == 0
    assert result.prediction.confidence == pytest.approx(0.55)
    assert result.config_name == "weak-direction"


def test_mtf_shadow_rejects_invalid_confidence_gate() -> None:
    market = sample_market(800)
    authoritative = make_features(market)

    with pytest.raises(ValueError, match="min_confidence"):
        evaluate_multi_timeframe_shadow(
            market,
            authoritative,
            market.index[-4],
            min_train_rows=100,
            max_train_rows=200,
            min_confidence=1.1,
        )

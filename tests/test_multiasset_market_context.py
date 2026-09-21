import numpy as np
import pandas as pd
import pytest

from ai_trading.config import ModelConfig
from ai_trading.multiasset_market_context import prepare_multiasset_market_context


def market(seed: int, n: int = 120, *, offset_minutes: int = 0) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    index = pd.date_range(
        "2025-01-01",
        periods=n,
        freq="D",
    ) + pd.Timedelta(minutes=offset_minutes)
    returns = rng.normal(0.0003, 0.01, n)
    close = 100.0 * np.cumprod(1.0 + returns)
    open_ = close * (1.0 + rng.normal(0.0, 0.001, n))
    return pd.DataFrame(
        {
            "Open": open_,
            "High": np.maximum(open_, close) * 1.005,
            "Low": np.minimum(open_, close) * 0.995,
            "Close": close,
            "Volume": 1000.0 + np.arange(n),
        },
        index=index,
    )


def test_prepare_multiasset_market_context_builds_aligned_inputs() -> None:
    markets = {"A": market(1), "B": market(2)}

    context = prepare_multiasset_market_context(markets, ModelConfig())

    assert context.execution_time == str(markets["A"].index[-1])
    assert set(context.closes) == {"A", "B"}
    assert set(context.opens) == {"A", "B"}
    assert set(context.features_by_symbol) == {"A", "B"}
    assert set(context.labels_by_symbol) == {"A", "B"}
    assert list(context.returns.columns) == ["A", "B"]
    assert len(context.returns) >= 20


def test_prepare_multiasset_market_context_rejects_unaligned_latest_bar() -> None:
    with pytest.raises(ValueError, match="not aligned"):
        prepare_multiasset_market_context(
            {"A": market(1), "B": market(2, offset_minutes=5)},
            ModelConfig(),
        )


def test_prepare_multiasset_market_context_rejects_insufficient_assets() -> None:
    with pytest.raises(ValueError, match="at least two"):
        prepare_multiasset_market_context({"A": market(1)}, ModelConfig())


def test_prepare_multiasset_market_context_rejects_short_history() -> None:
    with pytest.raises(ValueError, match="Insufficient data"):
        prepare_multiasset_market_context(
            {"A": market(1, n=39), "B": market(2, n=39)},
            ModelConfig(),
        )


def test_prepare_multiasset_market_context_rejects_missing_columns() -> None:
    broken = market(1).drop(columns=["Volume"])
    with pytest.raises(ValueError, match="Missing market columns"):
        prepare_multiasset_market_context(
            {"A": broken, "B": market(2)},
            ModelConfig(),
        )


@pytest.mark.parametrize("invalid_price", [0.0, -1.0, np.nan, np.inf])
def test_prepare_multiasset_market_context_rejects_invalid_latest_prices(
    invalid_price: float,
) -> None:
    broken = market(1)
    broken.loc[broken.index[-1], "Open"] = invalid_price

    with pytest.raises(ValueError, match="Invalid latest execution prices"):
        prepare_multiasset_market_context(
            {"A": broken, "B": market(2)},
            ModelConfig(),
        )

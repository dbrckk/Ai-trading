from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from .config import ModelConfig
from .features import make_features, make_labels


@dataclass(frozen=True)
class MultiAssetMarketContext:
    closes: dict[str, pd.Series]
    opens: dict[str, pd.Series]
    features_by_symbol: dict[str, pd.DataFrame]
    labels_by_symbol: dict[str, pd.Series]
    execution_time: str
    returns: pd.DataFrame


def prepare_multiasset_market_context(
    markets: dict[str, pd.DataFrame],
    model_config: ModelConfig,
) -> MultiAssetMarketContext:
    if len(markets) < 2:
        raise ValueError("Need at least two assets")

    closes: dict[str, pd.Series] = {}
    opens: dict[str, pd.Series] = {}
    execution_times: set[str] = set()
    features_by_symbol: dict[str, pd.DataFrame] = {}
    labels_by_symbol: dict[str, pd.Series] = {}

    required_columns = {"Open", "High", "Low", "Close", "Volume"}
    for symbol, market in markets.items():
        if len(market) < 40:
            raise ValueError(f"Insufficient data for {symbol}")
        missing_columns = required_columns.difference(market.columns)
        if missing_columns:
            raise ValueError(
                f"Missing market columns for {symbol}: {sorted(missing_columns)}"
            )

        latest_open = float(market["Open"].iloc[-1])
        latest_close = float(market["Close"].iloc[-1])
        if (
            not np.isfinite(latest_open)
            or not np.isfinite(latest_close)
            or latest_open <= 0.0
            or latest_close <= 0.0
        ):
            raise ValueError(f"Invalid latest execution prices for {symbol}")

        closes[symbol] = market["Close"].astype(float)
        opens[symbol] = market["Open"].astype(float)
        execution_times.add(str(market.index[-1]))
        features_by_symbol[symbol] = make_features(market)
        labels_by_symbol[symbol] = make_labels(
            market,
            horizon_bars=model_config.horizon_bars,
            return_threshold=model_config.return_threshold,
        )

    if len(execution_times) != 1:
        raise ValueError("Assets are not aligned on the same latest bar")
    execution_time = next(iter(execution_times))

    close_frame = pd.DataFrame(closes).dropna()
    returns = close_frame.pct_change().dropna()
    if len(returns) < 20:
        raise ValueError("Insufficient aligned return history")

    return MultiAssetMarketContext(
        closes=closes,
        opens=opens,
        features_by_symbol=features_by_symbol,
        labels_by_symbol=labels_by_symbol,
        execution_time=execution_time,
        returns=returns,
    )

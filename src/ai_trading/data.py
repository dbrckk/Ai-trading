from __future__ import annotations

from dataclasses import dataclass
from time import sleep
from typing import Protocol

import numpy as np
import pandas as pd
import yfinance as yf


class MarketDataProvider(Protocol):
    """Minimal provider contract used by the trading runtime."""

    name: str

    def download(self, symbol: str, *, period: str, interval: str) -> pd.DataFrame: ...


@dataclass(frozen=True)
class YahooFinanceProvider:
    name: str = "yahoo"

    def download(self, symbol: str, *, period: str, interval: str) -> pd.DataFrame:
        return yf.download(
            symbol,
            period=period,
            interval=interval,
            auto_adjust=True,
            progress=False,
            threads=False,
        )


DEFAULT_MARKET_DATA_PROVIDERS: tuple[MarketDataProvider, ...] = (YahooFinanceProvider(),)

_OHLC_COLUMNS = ("Open", "High", "Low", "Close")
_HISTORY_COLUMNS = (*_OHLC_COLUMNS, "Volume")


def _normalize_history_frame(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        raise ValueError("market data provider returned an empty frame")

    frame = df.copy()
    if isinstance(frame.columns, pd.MultiIndex):
        frame.columns = frame.columns.get_level_values(0)

    missing = set(_HISTORY_COLUMNS).difference(frame.columns)
    if missing:
        raise ValueError(f"Missing columns: {sorted(missing)}")

    result = frame.loc[:, list(_HISTORY_COLUMNS)].copy()
    for column in _HISTORY_COLUMNS:
        result[column] = pd.to_numeric(result[column], errors="coerce")

    result["Volume"] = result["Volume"].fillna(0.0)
    result = result.dropna(subset=list(_OHLC_COLUMNS))
    if result.empty:
        raise ValueError("market data provider returned no usable OHLC rows")

    result = result.sort_index()
    if result.index.has_duplicates:
        result = result.loc[~result.index.duplicated(keep="last")].copy()

    prices = result.loc[:, list(_OHLC_COLUMNS)]
    if not np.isfinite(prices.to_numpy(dtype=float)).all():
        raise ValueError("market data contains non-finite OHLC prices")
    if (prices <= 0.0).any().any():
        raise ValueError("market data contains non-positive OHLC prices")

    violations = (
        (result["High"] < result["Low"])
        | (result["High"] < result["Open"])
        | (result["High"] < result["Close"])
        | (result["Low"] > result["Open"])
        | (result["Low"] > result["Close"])
    )
    if bool(violations.any()):
        raise ValueError("market data contains inconsistent OHLC rows")

    return result


def load_history(
    symbol: str,
    period: str = "5y",
    interval: str = "1d",
    *,
    max_attempts: int = 3,
    retry_backoff_seconds: float = 0.25,
    providers: tuple[MarketDataProvider, ...] | None = None,
) -> pd.DataFrame:
    if max_attempts < 1:
        raise ValueError("max_attempts must be at least 1")
    if retry_backoff_seconds < 0:
        raise ValueError("retry_backoff_seconds must be non-negative")

    provider_chain = DEFAULT_MARKET_DATA_PROVIDERS if providers is None else providers
    if not provider_chain:
        raise ValueError("providers must contain at least one market data provider")

    last_error: Exception | None = None
    attempts = 0
    for provider in provider_chain:
        for attempt in range(max_attempts):
            attempts += 1
            try:
                frame = provider.download(symbol, period=period, interval=interval)
                return _normalize_history_frame(frame)
            except Exception as exc:  # noqa: BLE001 - providers raise backend-specific errors
                last_error = exc
                if attempt + 1 < max_attempts:
                    sleep(retry_backoff_seconds * (2**attempt))

    raise ValueError(
        f"Failed to load valid market data for {symbol!r} after {attempts} provider attempts"
    ) from last_error

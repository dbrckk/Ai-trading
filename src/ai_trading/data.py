from __future__ import annotations

import pandas as pd
import yfinance as yf


def load_history(symbol: str, period: str = "5y", interval: str = "1d") -> pd.DataFrame:
    df = yf.download(
        symbol,
        period=period,
        interval=interval,
        auto_adjust=True,
        progress=False,
        threads=False,
    )
    if df.empty:
        raise ValueError(f"No market data returned for {symbol!r}")

    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    required = {"Open", "High", "Low", "Close", "Volume"}
    missing = required.difference(df.columns)
    if missing:
        raise ValueError(f"Missing columns: {sorted(missing)}")

    return df.loc[:, ["Open", "High", "Low", "Close", "Volume"]].dropna().copy()

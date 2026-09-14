from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class ChaosScenario:
    name: str
    step: int
    symbol: str | None = None


def apply_chaos(
    markets: dict[str, pd.DataFrame],
    scenario: ChaosScenario,
    *,
    current_step: int,
) -> dict[str, pd.DataFrame]:
    copied = {symbol: df.copy() for symbol, df in markets.items()}
    if current_step != scenario.step:
        return copied

    if scenario.name == "nan_last_close":
        if scenario.symbol is None:
            raise ValueError("nan_last_close requires symbol")
        copied[scenario.symbol].iloc[-1, copied[scenario.symbol].columns.get_loc("Close")] = float("nan")
        return copied

    if scenario.name == "duplicate_timestamp":
        if scenario.symbol is None:
            raise ValueError("duplicate_timestamp requires symbol")
        frame = copied[scenario.symbol]
        copied[scenario.symbol] = pd.concat([frame, frame.iloc[[-1]]])
        return copied

    if scenario.name == "ohlc_violation":
        if scenario.symbol is None:
            raise ValueError("ohlc_violation requires symbol")
        frame = copied[scenario.symbol]
        frame.iloc[-1, frame.columns.get_loc("High")] = (
            frame.iloc[-1, frame.columns.get_loc("Low")] - 1.0
        )
        return copied

    if scenario.name == "stale_prices":
        if scenario.symbol is None:
            raise ValueError("stale_prices requires symbol")
        frame = copied[scenario.symbol]
        last_close = float(frame["Close"].iloc[-20])
        frame.loc[frame.index[-20:], "Close"] = last_close
        frame.loc[frame.index[-20:], "Open"] = last_close
        frame.loc[frame.index[-20:], "High"] = last_close
        frame.loc[frame.index[-20:], "Low"] = last_close
        return copied

    raise ValueError(f"unknown chaos scenario: {scenario.name}")

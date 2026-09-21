from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class DataQualityReport:
    score: float
    completeness: float
    duplicate_fraction: float
    invalid_price_fraction: float
    ohlc_violation_fraction: float
    stale_fraction: float
    valid: bool
    reasons: tuple[str, ...]
    gap_fraction: float = 0.0


def evaluate_market_data_quality(
    df: pd.DataFrame,
    *,
    lookback: int = 100,
    min_score: float = 0.95,
) -> DataQualityReport:
    if lookback < 3:
        raise ValueError("lookback must be at least 3")
    if not 0.0 <= min_score <= 1.0:
        raise ValueError("min_score must be in [0, 1]")

    required_columns = ["Open", "High", "Low", "Close"]
    missing_columns = [column for column in required_columns if column not in df.columns]
    if missing_columns:
        return DataQualityReport(
            score=0.0,
            completeness=0.0,
            duplicate_fraction=0.0,
            invalid_price_fraction=1.0,
            ohlc_violation_fraction=1.0,
            stale_fraction=1.0,
            gap_fraction=1.0,
            valid=False,
            reasons=(f"missing columns: {', '.join(missing_columns)}",),
        )

    sample = df.loc[:, required_columns].tail(lookback).copy()
    if sample.empty:
        return DataQualityReport(
            score=0.0,
            completeness=0.0,
            duplicate_fraction=0.0,
            invalid_price_fraction=1.0,
            ohlc_violation_fraction=1.0,
            stale_fraction=1.0,
            gap_fraction=1.0,
            valid=False,
            reasons=("empty market data",),
        )

    completeness = float(sample.notna().mean().mean())
    duplicate_fraction = float(df.index.duplicated(keep=False).mean())

    invalid_prices = (sample <= 0).any(axis=1)
    invalid_price_fraction = float(invalid_prices.mean())

    high = sample["High"]
    low = sample["Low"]
    open_ = sample["Open"]
    close = sample["Close"]
    violations = (
        (high < low)
        | (high < open_)
        | (high < close)
        | (low > open_)
        | (low > close)
    )
    ohlc_violation_fraction = float(violations.fillna(True).mean())

    close_changes = close.pct_change().abs()
    stale_fraction = float((close_changes.fillna(0.0) == 0.0).mean())

    gap_fraction = 1.0
    if isinstance(sample.index, pd.DatetimeIndex) and len(sample.index) >= 3:
        deltas = sample.index.to_series().diff().dropna()
        positive = deltas[deltas > pd.Timedelta(0)]
        if not positive.empty:
            cadence = positive.median()
            if cadence > pd.Timedelta(0):
                gap_fraction = float((positive > cadence * 1.5).mean())

    score = (
        0.40 * completeness
        + 0.15 * (1.0 - min(1.0, duplicate_fraction))
        + 0.15 * (1.0 - min(1.0, invalid_price_fraction))
        + 0.15 * (1.0 - min(1.0, ohlc_violation_fraction))
        + 0.10 * (1.0 - min(1.0, stale_fraction))
        + 0.05 * (1.0 - min(1.0, gap_fraction))
    )

    reasons: list[str] = []
    if completeness < 0.99:
        reasons.append("incomplete OHLC data")
    if duplicate_fraction > 0:
        reasons.append("duplicate timestamps")
    if invalid_price_fraction > 0:
        reasons.append("non-positive prices")
    if ohlc_violation_fraction > 0:
        reasons.append("OHLC consistency violations")
    if stale_fraction > 0.20:
        reasons.append("excessive stale closes")
    if gap_fraction > 0.05:
        reasons.append("excessive cadence gaps")

    return DataQualityReport(
        score=float(max(0.0, min(1.0, score))),
        completeness=completeness,
        duplicate_fraction=duplicate_fraction,
        invalid_price_fraction=invalid_price_fraction,
        ohlc_violation_fraction=ohlc_violation_fraction,
        stale_fraction=stale_fraction,
        gap_fraction=gap_fraction,
        valid=score >= min_score and not reasons,
        reasons=tuple(reasons),
    )

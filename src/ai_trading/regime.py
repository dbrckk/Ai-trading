from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class MarketRegime:
    trend: str
    volatility: str

    @property
    def name(self) -> str:
        return f"{self.trend}_{self.volatility}"


def detect_regime(row: pd.Series) -> MarketRegime:
    trend_10 = float(row.get("trend_10", 0.0))
    trend_30 = float(row.get("trend_30", 0.0))
    vol_10 = float(row.get("vol_10", 0.0))

    trend_score = 0.6 * trend_10 + 0.4 * trend_30
    if trend_score > 0.01:
        trend = "bull"
    elif trend_score < -0.01:
        trend = "bear"
    else:
        trend = "sideways"

    volatility = "high_vol" if vol_10 >= 0.02 else "normal_vol"
    return MarketRegime(trend=trend, volatility=volatility)

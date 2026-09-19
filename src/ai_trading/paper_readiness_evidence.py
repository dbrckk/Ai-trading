from __future__ import annotations

from functools import lru_cache

import pandas as pd

from .bootstrap_robustness import bootstrap_equity_curve


@lru_cache(maxsize=16)
def bootstrap_positive_probability(equities: tuple[float, ...]) -> float | None:
    if len(equities) < 3:
        return None
    report = bootstrap_equity_curve(pd.Series(equities, dtype=float))
    return report.probability_positive

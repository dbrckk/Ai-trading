"""Research-only guard: never refit historical selectors on prospective bars.

The registered 2026-10-26 study treats all later market observations as
forward evidence. Historical selector workflows may still be rerun, but
their *input* must be restricted to strictly earlier candle opening times.
This helper does not change the live paper engine or capture workflow.
"""

from __future__ import annotations

import pandas as pd

FROZEN_PROSPECTIVE_START_UTC = pd.Timestamp("2026-10-26T00:00:00+00:00")


def frozen_preprospective_history(
    frame: pd.DataFrame, *, symbol: str
) -> pd.DataFrame:
    """Fail closed on ambiguous clocks and missing pre-study history."""
    if (
        not symbol.strip()
        or not isinstance(frame.index, pd.DatetimeIndex)
        or frame.index.tz is None
        or frame.index.hasnans
        or frame.index.has_duplicates
        or not frame.index.is_monotonic_increasing
    ):
        raise ValueError("retrospective research requires ordered timezone-aware bars")
    opening_times = frame.index.tz_convert("UTC")
    history = frame.loc[opening_times < FROZEN_PROSPECTIVE_START_UTC].copy()
    if history.empty:
        raise ValueError(f"{symbol}: no verifiable pre-prospective bars remain")
    if not (history.index.tz_convert("UTC") < FROZEN_PROSPECTIVE_START_UTC).all():
        raise ValueError(f"{symbol}: prospective bar leaked into historical research")
    return history

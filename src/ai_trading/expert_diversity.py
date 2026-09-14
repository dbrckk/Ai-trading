from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class DiversityReport:
    max_pair_correlation: float
    mean_pair_correlation: float
    diversified: bool


def evaluate_expert_diversity(
    expert_returns: pd.DataFrame,
    *,
    max_pair_correlation: float = 0.85,
) -> DiversityReport:
    clean = expert_returns.astype(float).dropna()
    if clean.shape[1] < 2:
        return DiversityReport(0.0, 0.0, True)

    corr = clean.corr().abs()
    pairs: list[float] = []
    for i, left in enumerate(corr.index):
        for right in corr.columns[i + 1 :]:
            value = corr.at[left, right]
            if pd.notna(value):
                pairs.append(float(value))

    if not pairs:
        return DiversityReport(0.0, 0.0, True)

    maximum = max(pairs)
    mean = sum(pairs) / len(pairs)
    return DiversityReport(
        max_pair_correlation=maximum,
        mean_pair_correlation=mean,
        diversified=maximum <= max_pair_correlation,
    )

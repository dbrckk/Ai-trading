from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RegimeValidation:
    valid: bool
    covered_regimes: int
    profitable_regimes: int
    worst_regime_return: float
    reason: str


def validate_regime_returns(
    regime_returns: dict[str, float],
    *,
    min_regimes: int = 2,
    min_profitable_fraction: float = 0.5,
    worst_regime_floor: float = -0.10,
) -> RegimeValidation:
    if len(regime_returns) < min_regimes:
        return RegimeValidation(
            False,
            len(regime_returns),
            sum(v > 0 for v in regime_returns.values()),
            min(regime_returns.values(), default=0.0),
            "insufficient regime coverage",
        )

    profitable = sum(v > 0 for v in regime_returns.values())
    fraction = profitable / len(regime_returns)
    worst = min(regime_returns.values())

    if fraction < min_profitable_fraction:
        return RegimeValidation(
            False,
            len(regime_returns),
            profitable,
            worst,
            "insufficient profitable regime coverage",
        )
    if worst < worst_regime_floor:
        return RegimeValidation(
            False,
            len(regime_returns),
            profitable,
            worst,
            "worst regime loss exceeds floor",
        )

    return RegimeValidation(
        True,
        len(regime_returns),
        profitable,
        worst,
        "regime validation passed",
    )

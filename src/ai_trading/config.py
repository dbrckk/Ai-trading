from dataclasses import dataclass
from math import isfinite


@dataclass(frozen=True)
class RiskConfig:
    starting_cash: float = 100_000.0
    max_position_fraction: float = 0.10
    max_daily_loss_fraction: float = 0.02
    max_drawdown_fraction: float = 0.10
    min_confidence: float = 0.56
    transaction_cost_bps: float = 2.0
    slippage_bps: float = 1.0
    # Optional same-direction turnover filter; disabled until backtested.
    min_rebalance_fraction: float = 0.0

    def __post_init__(self) -> None:
        if not isfinite(self.starting_cash) or self.starting_cash <= 0:
            raise ValueError("starting_cash must be positive and finite")
        for name in (
            "max_position_fraction",
            "max_daily_loss_fraction",
            "max_drawdown_fraction",
        ):
            value = float(getattr(self, name))
            if not 0.0 < value <= 1.0:
                raise ValueError(f"{name} must be in (0, 1]")
        if not 0.0 <= self.min_confidence <= 1.0:
            raise ValueError("min_confidence must be in [0, 1]")
        if any(
            not isfinite(value) or value < 0
            for value in (self.transaction_cost_bps, self.slippage_bps)
        ):
            raise ValueError("transaction costs and slippage must be finite and non-negative")
        if (
            not isfinite(self.min_rebalance_fraction)
            or not 0.0 <= self.min_rebalance_fraction <= 1.0
        ):
            raise ValueError("min_rebalance_fraction must be finite and in [0, 1]")


@dataclass(frozen=True)
class ModelConfig:
    horizon_bars: int = 1
    return_threshold: float = 0.001

    def __post_init__(self) -> None:
        if self.horizon_bars < 1:
            raise ValueError("horizon_bars must be at least 1")
        if not isfinite(self.return_threshold) or self.return_threshold < 0:
            raise ValueError("return_threshold must be finite and non-negative")

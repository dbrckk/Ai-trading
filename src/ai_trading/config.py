from dataclasses import dataclass


@dataclass(frozen=True)
class RiskConfig:
    starting_cash: float = 100_000.0
    max_position_fraction: float = 0.10
    max_daily_loss_fraction: float = 0.02
    max_drawdown_fraction: float = 0.10
    min_confidence: float = 0.56
    transaction_cost_bps: float = 2.0
    slippage_bps: float = 1.0


@dataclass(frozen=True)
class ModelConfig:
    horizon_bars: int = 1
    return_threshold: float = 0.001

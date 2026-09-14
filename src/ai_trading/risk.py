from __future__ import annotations

from dataclasses import dataclass

from .config import RiskConfig
from .model import Prediction


@dataclass(frozen=True)
class PortfolioSnapshot:
    equity: float
    peak_equity: float
    day_start_equity: float
    current_position_value: float = 0.0


@dataclass(frozen=True)
class RiskDecision:
    approved: bool
    side: int
    target_notional: float
    reason: str


class RiskEngine:
    def __init__(self, config: RiskConfig) -> None:
        self.config = config

    def evaluate(self, prediction: Prediction, portfolio: PortfolioSnapshot) -> RiskDecision:
        if portfolio.equity <= 0:
            return RiskDecision(False, 0, 0.0, "non-positive equity")

        drawdown = 1.0 - portfolio.equity / max(portfolio.peak_equity, portfolio.equity)
        if drawdown >= self.config.max_drawdown_fraction:
            return RiskDecision(False, 0, 0.0, "max drawdown reached")

        daily_loss = 1.0 - portfolio.equity / max(portfolio.day_start_equity, portfolio.equity)
        if daily_loss >= self.config.max_daily_loss_fraction:
            return RiskDecision(False, 0, 0.0, "daily loss limit reached")

        if prediction.side == 0:
            return RiskDecision(True, 0, 0.0, "model is flat")

        if prediction.confidence < self.config.min_confidence:
            return RiskDecision(False, 0, 0.0, "confidence below threshold")

        confidence_scale = min(1.0, max(0.0, (prediction.confidence - 0.5) / 0.5))
        target = (
            portfolio.equity
            * self.config.max_position_fraction
            * confidence_scale
        )
        return RiskDecision(True, prediction.side, target, "approved")

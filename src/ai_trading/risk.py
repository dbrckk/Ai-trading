from __future__ import annotations

from dataclasses import dataclass
from math import isfinite

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
    # A risk stop rejects new exposure but must close any existing position.
    # Execution paths treat this as exit-only, never as trade approval.
    liquidate_existing: bool = False


class RiskEngine:
    def __init__(self, config: RiskConfig) -> None:
        self.config = config

    def evaluate(self, prediction: Prediction, portfolio: PortfolioSnapshot) -> RiskDecision:
        # Invalid portfolio evidence must never authorize new exposure or a
        # forced exit at an untrustworthy price/state.
        if not all(
            isfinite(value)
            for value in (
                portfolio.equity,
                portfolio.peak_equity,
                portfolio.day_start_equity,
                portfolio.current_position_value,
            )
        ) or portfolio.peak_equity <= 0 or portfolio.day_start_equity <= 0:
            return RiskDecision(False, 0, 0.0, "invalid portfolio state")

        if portfolio.equity <= 0:
            return RiskDecision(False, 0, 0.0, "non-positive equity", liquidate_existing=True)

        drawdown = 1.0 - portfolio.equity / max(portfolio.peak_equity, portfolio.equity)
        if drawdown >= self.config.max_drawdown_fraction:
            return RiskDecision(False, 0, 0.0, "max drawdown reached", liquidate_existing=True)

        daily_loss = 1.0 - portfolio.equity / max(portfolio.day_start_equity, portfolio.equity)
        if daily_loss >= self.config.max_daily_loss_fraction:
            return RiskDecision(False, 0, 0.0, "daily loss limit reached", liquidate_existing=True)

        if (
            prediction.side not in (-1, 0, 1)
            or not isfinite(prediction.confidence)
            or not 0.0 <= prediction.confidence <= 1.0
        ):
            return RiskDecision(False, 0, 0.0, "invalid model prediction")

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

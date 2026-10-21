from ai_trading.config import RiskConfig
from ai_trading.model import Prediction
from ai_trading.risk import PortfolioSnapshot, RiskEngine


def test_low_confidence_is_rejected() -> None:
    engine = RiskEngine(RiskConfig(min_confidence=0.60))
    pred = Prediction(side=1, confidence=0.55, probabilities={-1: 0.2, 0: 0.25, 1: 0.55})
    snap = PortfolioSnapshot(100_000, 100_000, 100_000)
    decision = engine.evaluate(pred, snap)
    assert not decision.approved


def test_drawdown_limit_is_fail_closed() -> None:
    engine = RiskEngine(RiskConfig(max_drawdown_fraction=0.10))
    pred = Prediction(side=1, confidence=0.90, probabilities={-1: 0.05, 0: 0.05, 1: 0.90})
    snap = PortfolioSnapshot(89_000, 100_000, 100_000)
    decision = engine.evaluate(pred, snap)
    assert not decision.approved
    assert decision.side == 0
    assert decision.liquidate_existing is True
    assert decision.target_notional == 0.0


def test_daily_loss_stop_marks_existing_position_for_exit() -> None:
    engine = RiskEngine(RiskConfig(max_daily_loss_fraction=0.02))
    pred = Prediction(
        side=1, confidence=0.99, probabilities={-1: 0.0, 0: 0.01, 1: 0.99}
    )
    snap = PortfolioSnapshot(
        equity=97_500,
        peak_equity=100_000,
        day_start_equity=100_000,
        current_position_value=10_000,
    )

    decision = engine.evaluate(pred, snap)

    assert decision.approved is False
    assert decision.liquidate_existing is True
    assert decision.side == 0
    assert decision.reason == "daily loss limit reached"


def test_low_confidence_rejection_does_not_force_liquidation() -> None:
    engine = RiskEngine(RiskConfig(min_confidence=0.70))
    pred = Prediction(
        side=1, confidence=0.60, probabilities={-1: 0.10, 0: 0.30, 1: 0.60}
    )
    snap = PortfolioSnapshot(
        equity=100_000,
        peak_equity=100_000,
        day_start_equity=100_000,
        current_position_value=10_000,
    )

    decision = engine.evaluate(pred, snap)

    assert decision.approved is False
    assert decision.liquidate_existing is False

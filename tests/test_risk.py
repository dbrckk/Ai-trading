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

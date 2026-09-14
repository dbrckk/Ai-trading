from ai_trading.expert_uncertainty import measure_expert_uncertainty
from ai_trading.model import Prediction


def prediction(side: int, probs: dict[int, float]) -> Prediction:
    return Prediction(
        side=side,
        confidence=max(probs.values()),
        probabilities=probs,
    )


def test_identical_experts_have_zero_disagreement() -> None:
    pred = prediction(1, {-1: 0.1, 0: 0.1, 1: 0.8})
    report = measure_expert_uncertainty({"a": pred, "b": pred})
    assert report.disagreement == 0.0
    assert report.risk_multiplier == 1.0


def test_conflicting_experts_reduce_risk_multiplier() -> None:
    long = prediction(1, {-1: 0.0, 0: 0.0, 1: 1.0})
    short = prediction(-1, {-1: 1.0, 0: 0.0, 1: 0.0})
    report = measure_expert_uncertainty({"long": long, "short": short})
    assert report.disagreement > 0.0
    assert report.risk_multiplier < 1.0

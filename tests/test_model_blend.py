from ai_trading.model import Prediction
from ai_trading.model_blend import BlendComponent, blend_predictions


def test_blend_prefers_higher_quality_model() -> None:
    long = Prediction(1, 0.8, {-1: 0.1, 0: 0.1, 1: 0.8})
    short = Prediction(-1, 0.8, {-1: 0.8, 0: 0.1, 1: 0.1})

    blended = blend_predictions(
        [
            BlendComponent("good", long, 0.9),
            BlendComponent("bad", short, 0.1),
        ]
    )
    assert blended.side == 1
    assert blended.probabilities[1] > blended.probabilities[-1]

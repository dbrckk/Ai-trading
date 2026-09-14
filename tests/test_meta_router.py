from ai_trading.meta_router import MetaContext, route_predictions
from ai_trading.model import Prediction


def test_meta_router_prefers_contextually_better_model() -> None:
    long = Prediction(1, 0.8, {-1: 0.1, 0: 0.1, 1: 0.8})
    short = Prediction(-1, 0.8, {-1: 0.8, 0: 0.1, 1: 0.1})
    routed = route_predictions(
        {"long_model": long, "short_model": short},
        {"long_model": 0.9, "short_model": 0.1},
    )
    assert routed.prediction.side == 1
    assert routed.weights["long_model"] > routed.weights["short_model"]


def test_meta_context_is_constructible() -> None:
    context = MetaContext(
        symbol="GC=F",
        regime="bull_normal_vol",
        volatility_bucket="normal",
        drawdown_bucket="low",
    )
    assert context.symbol == "GC=F"

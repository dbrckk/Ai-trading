from ai_trading.alpha_attribution import build_alpha_contribution


def test_alpha_attribution_tracks_model_and_regime() -> None:
    item = build_alpha_contribution(
        symbol="GC=F",
        model="river",
        regime="bull_normal_vol",
        pnl=250.0,
        portfolio_equity=100_000.0,
    )
    assert item.symbol == "GC=F"
    assert item.model == "river"
    assert item.regime == "bull_normal_vol"
    assert item.return_contribution == 0.0025

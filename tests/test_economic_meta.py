from ai_trading.economic_meta import EconomicMetaStats, economic_route_weight, update_economic_meta


def test_profitable_low_cost_model_scores_better() -> None:
    base = EconomicMetaStats()
    good = update_economic_meta(
        base,
        pnl=500.0,
        turnover=2_000.0,
        costs=10.0,
        drawdown=0.01,
        equity=100_000.0,
    )
    bad = update_economic_meta(
        base,
        pnl=-200.0,
        turnover=20_000.0,
        costs=80.0,
        drawdown=0.08,
        equity=100_000.0,
    )
    assert good.score > bad.score
    assert economic_route_weight(good) > economic_route_weight(bad)

from ai_trading.performance import PerformanceMetrics
from ai_trading.promotion import PromotionPolicy, evaluate_multi_period_challenger


def metric(total_return: float, sharpe: float, drawdown: float) -> PerformanceMetrics:
    return PerformanceMetrics(
        total_return=total_return,
        annualized_return=total_return,
        annualized_volatility=0.10,
        sharpe=sharpe,
        sortino=sharpe + 0.1,
        max_drawdown=drawdown,
        calmar=1.0,
    )


def test_multi_period_promotion_requires_consistency() -> None:
    champion = [metric(0.10, 0.8, 0.08) for _ in range(5)]
    challenger = [
        metric(0.14, 1.0, 0.08),
        metric(0.13, 1.0, 0.08),
        metric(0.12, 1.0, 0.08),
        metric(0.09, 0.7, 0.08),
        metric(0.08, 0.6, 0.08),
    ]
    decision = evaluate_multi_period_challenger(
        champion,
        challenger,
        PromotionPolicy(min_period_win_rate=0.60),
    )
    assert decision.promote

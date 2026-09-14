from ai_trading.performance import PerformanceMetrics
from ai_trading.promotion import PromotionPolicy, evaluate_challenger


def metrics(total_return: float, sharpe: float, max_drawdown: float) -> PerformanceMetrics:
    return PerformanceMetrics(
        total_return=total_return,
        annualized_return=total_return,
        annualized_volatility=0.10,
        sharpe=sharpe,
        sortino=sharpe,
        max_drawdown=max_drawdown,
        calmar=1.0,
    )


def test_promotes_materially_better_challenger() -> None:
    champion = metrics(0.10, 0.8, 0.08)
    challenger = metrics(0.14, 1.05, 0.09)
    decision = evaluate_challenger(champion, challenger)
    assert decision.promote


def test_rejects_excess_drawdown() -> None:
    champion = metrics(0.10, 0.8, 0.08)
    challenger = metrics(0.20, 1.2, 0.15)
    policy = PromotionPolicy(max_drawdown_increase=0.02)
    decision = evaluate_challenger(champion, challenger, policy)
    assert not decision.promote

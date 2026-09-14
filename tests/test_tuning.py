from ai_trading.performance import PerformanceMetrics
from ai_trading.tuning import objective_score


def metric(total_return: float, sharpe: float, sortino: float, drawdown: float) -> PerformanceMetrics:
    return PerformanceMetrics(
        total_return=total_return,
        annualized_return=total_return,
        annualized_volatility=0.10,
        sharpe=sharpe,
        sortino=sortino,
        max_drawdown=drawdown,
        calmar=1.0,
    )


def test_objective_prefers_similar_return_with_lower_drawdown() -> None:
    safer = metric(0.20, 1.1, 1.4, 0.08)
    riskier = metric(0.21, 1.1, 1.4, 0.18)
    assert objective_score(safer) > objective_score(riskier)

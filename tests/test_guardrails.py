from ai_trading.drift import DriftReport
from ai_trading.guardrails import HealthPolicy, evaluate_health
from ai_trading.performance import PerformanceMetrics


def metrics(sharpe: float = 1.0, drawdown: float = 0.08) -> PerformanceMetrics:
    return PerformanceMetrics(
        total_return=0.2,
        annualized_return=0.2,
        annualized_volatility=0.1,
        sharpe=sharpe,
        sortino=1.2,
        max_drawdown=drawdown,
        calmar=2.0,
    )


def test_health_rolls_back_on_drift() -> None:
    drift = DriftReport(2.0, 0.1, True, ("feature distribution drift",))
    decision = evaluate_health(metrics(), drift)
    assert decision.rollback


def test_health_accepts_healthy_model() -> None:
    drift = DriftReport(0.1, 0.1, False, ())
    decision = evaluate_health(metrics(), drift, HealthPolicy(min_sharpe=0.5, max_drawdown=0.10))
    assert decision.healthy
    assert not decision.rollback

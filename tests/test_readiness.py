from ai_trading.performance import PerformanceMetrics
from ai_trading.readiness import ReadinessPolicy, evaluate_readiness


def good_metrics() -> PerformanceMetrics:
    return PerformanceMetrics(
        total_return=0.12,
        annualized_return=0.12,
        annualized_volatility=0.08,
        sharpe=1.2,
        sortino=1.5,
        max_drawdown=0.06,
        calmar=2.0,
    )


def test_readiness_passes_strong_burn_in() -> None:
    report = evaluate_readiness(
        metrics=good_metrics(),
        burn_in_bars=200,
        bootstrap_probability_positive=0.80,
        regimes_covered=4,
        scheduler_errors=0,
    )
    assert report.ready
    assert report.checks_passed == report.checks_total


def test_readiness_rejects_short_burn_in() -> None:
    report = evaluate_readiness(
        metrics=good_metrics(),
        burn_in_bars=20,
        bootstrap_probability_positive=0.80,
        regimes_covered=4,
        scheduler_errors=0,
        policy=ReadinessPolicy(min_burn_in_bars=126),
    )
    assert not report.ready
    assert "insufficient burn-in duration" in report.reasons

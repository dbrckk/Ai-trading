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


def test_readiness_report_exposes_all_structured_checks() -> None:
    report = evaluate_readiness(
        metrics=good_metrics(),
        burn_in_bars=20,
        bootstrap_probability_positive=0.40,
        regimes_covered=1,
        scheduler_errors=2,
    )

    assert len(report.checks) == 8
    assert tuple(check.name for check in report.checks) == (
        "Burn-in bars",
        "Sharpe",
        "Sortino",
        "Max drawdown",
        "Total return",
        "Bootstrap confidence",
        "Regime coverage",
        "Scheduler errors",
    )
    by_name = {check.name: check for check in report.checks}
    assert by_name["Burn-in bars"].passed is False
    assert by_name["Burn-in bars"].value == 20
    assert by_name["Burn-in bars"].threshold == 126
    assert by_name["Burn-in bars"].comparison == ">="
    assert by_name["Scheduler errors"].passed is False
    assert by_name["Scheduler errors"].comparison == "<="

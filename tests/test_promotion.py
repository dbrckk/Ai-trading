import math
from dataclasses import replace

import pytest

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


def test_promotion_rejects_nonfinite_metrics_even_if_relative_checks_would_pass() -> None:
    champion = metrics(0.10, 0.8, 0.08)
    better = metrics(0.14, 1.05, 0.09)
    for field, value in (
        ("sharpe", math.nan),
        ("total_return", math.inf),
        ("max_drawdown", math.nan),
        ("sortino", math.nan),
    ):
        invalid = replace(better, **{field: value})
        decision = evaluate_challenger(champion, invalid)
        assert not decision.promote
        assert decision.reason == "non-finite promotion metrics"


def test_promotion_rejects_losing_challenger_outperforming_losing_champion() -> None:
    champion = metrics(-0.20, -2.0, 0.25)
    challenger = metrics(-0.05, -0.5, 0.20)
    decision = evaluate_challenger(champion, challenger)
    assert not decision.promote
    assert decision.reason == "challenger lacks positive net return"


def test_promotion_rejects_invalid_drawdown_or_policy() -> None:
    champion = metrics(0.10, 0.8, 0.08)
    better = metrics(0.14, 1.05, 0.09)
    result = evaluate_challenger(champion, replace(better, max_drawdown=-0.1))
    assert not result.promote
    assert result.reason == "invalid promotion drawdown"
    with pytest.raises(ValueError, match="finite"):
        PromotionPolicy(min_period_win_rate=math.nan)

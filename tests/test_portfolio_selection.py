from ai_trading.marginal_alpha import MarginalAlphaReport
from ai_trading.portfolio_selection import evaluate_portfolio_replacement


def test_replacement_requires_portfolio_and_score_improvement() -> None:
    marginal = MarginalAlphaReport(
        marginal_return=0.02,
        marginal_sharpe=0.1,
        marginal_drawdown=0.0,
        correlation_to_portfolio=0.2,
        improves_portfolio=True,
    )
    decision = evaluate_portfolio_replacement(
        marginal,
        incumbent_score=0.60,
        challenger_score=0.70,
    )
    assert decision.replace

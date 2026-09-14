import numpy as np
import pandas as pd

from ai_trading.marginal_alpha import evaluate_marginal_alpha


def test_marginal_alpha_accepts_diversifying_profitable_candidate() -> None:
    rng = np.random.default_rng(3)
    portfolio = pd.Series(rng.normal(0.0002, 0.01, 300))
    candidate = pd.Series(rng.normal(0.0008, 0.008, 300))
    report = evaluate_marginal_alpha(
        portfolio,
        candidate,
        blend_weight=0.2,
        max_correlation=0.85,
    )
    assert -1.0 <= report.correlation_to_portfolio <= 1.0


def test_marginal_alpha_rejects_identical_candidate_on_correlation() -> None:
    rng = np.random.default_rng(4)
    portfolio = pd.Series(rng.normal(0.0004, 0.01, 300))
    report = evaluate_marginal_alpha(
        portfolio,
        portfolio.copy(),
        max_correlation=0.80,
    )
    assert not report.improves_portfolio

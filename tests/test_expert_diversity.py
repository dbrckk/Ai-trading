import numpy as np
import pandas as pd

from ai_trading.expert_diversity import evaluate_expert_diversity


def test_diversity_rejects_nearly_identical_experts() -> None:
    x = np.linspace(-0.02, 0.02, 100)
    df = pd.DataFrame({"a": x, "b": x * 1.001})
    report = evaluate_expert_diversity(df, max_pair_correlation=0.8)
    assert not report.diversified
    assert report.max_pair_correlation > 0.99


def test_diversity_accepts_low_correlation_experts() -> None:
    rng = np.random.default_rng(7)
    df = pd.DataFrame(
        {
            "a": rng.normal(0, 1, 300),
            "b": rng.normal(0, 1, 300),
            "c": rng.normal(0, 1, 300),
        }
    )
    report = evaluate_expert_diversity(df, max_pair_correlation=0.8)
    assert report.diversified

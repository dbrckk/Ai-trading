import numpy as np
import pandas as pd

from ai_trading.stress_engine import StressPolicy, run_stress_test


def test_stress_engine_returns_risk_scale() -> None:
    rng = np.random.default_rng(5)
    returns = pd.DataFrame(
        {
            "A": rng.normal(0.0002, 0.01, 300),
            "B": rng.normal(0.0001, 0.015, 300),
            "C": rng.normal(0.0003, 0.02, 300),
        }
    )
    report = run_stress_test(
        returns,
        pd.Series({"A": 0.4, "B": 0.3, "C": 0.3}),
        policy=StressPolicy(
            max_loss=0.20,
            max_stressed_cvar=0.20,
            monte_carlo_paths=300,
            horizon_days=3,
        ),
    )
    assert 0.0 <= report.risk_scale <= 1.0
    assert report.worst_loss >= 0.0
    assert report.stressed_cvar >= 0.0


def test_stress_engine_deleverages_under_tight_loss_limit() -> None:
    rng = np.random.default_rng(8)
    returns = pd.DataFrame(
        {
            "A": rng.normal(0.0, 0.03, 250),
            "B": rng.normal(0.0, 0.03, 250),
        }
    )
    report = run_stress_test(
        returns,
        pd.Series({"A": 0.5, "B": 0.5}),
        policy=StressPolicy(
            max_loss=0.01,
            max_stressed_cvar=0.01,
            monte_carlo_paths=300,
            horizon_days=5,
        ),
    )
    assert report.risk_scale < 1.0

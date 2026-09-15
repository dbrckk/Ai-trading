import pandas as pd
import pytest

from ai_trading.bootstrap_robustness import BootstrapConfig, bootstrap_equity_curve


def test_bootstrap_is_deterministic_with_seed() -> None:
    curve = pd.Series([100.0, 101.0, 100.5, 102.0, 103.0, 104.0])

    first = bootstrap_equity_curve(
        curve,
        BootstrapConfig(simulations=200, seed=7, block_size=2),
    )
    second = bootstrap_equity_curve(
        curve,
        BootstrapConfig(simulations=200, seed=7, block_size=2),
    )

    assert first == second
    assert 0.0 <= first.probability_positive <= 1.0
    assert 0.0 <= first.probability_loss <= 1.0
    assert first.upper_max_drawdown >= 0.0


def test_bootstrap_rejects_too_short_curve() -> None:
    with pytest.raises(ValueError, match="at least three"):
        bootstrap_equity_curve(
            pd.Series([100.0, 101.0]),
            BootstrapConfig(simulations=100),
        )


def test_bootstrap_positive_curve_has_positive_median() -> None:
    curve = pd.Series([100.0, 101.0, 102.0, 103.0, 104.0, 105.0])

    report = bootstrap_equity_curve(
        curve,
        BootstrapConfig(simulations=300, seed=42, block_size=2),
    )

    assert report.median_return > 0.0
    assert report.probability_positive > 0.9

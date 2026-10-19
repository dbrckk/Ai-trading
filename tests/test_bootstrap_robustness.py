import numpy as np
import pandas as pd
import pytest

from ai_trading.bootstrap_robustness import (
    BootstrapConfig,
    _block_bootstrap,
    bootstrap_equity_curve,
)


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


@pytest.mark.parametrize(
    ("length", "block_size"),
    [(3, 1), (17, 5), (32, 32), (101, 3), (6131, 5)],
)
def test_vectorized_block_sampling_matches_original_rng_sequence(
    length: int, block_size: int
) -> None:
    returns = np.linspace(-0.01, 0.02, length)
    reference_rng = np.random.default_rng(123)
    expected: list[float] = []
    while len(expected) < length:
        start = int(reference_rng.integers(0, length - block_size + 1))
        expected.extend(returns[start : start + block_size])

    actual_rng = np.random.default_rng(123)
    actual = _block_bootstrap(returns, rng=actual_rng, block_size=block_size)
    np.testing.assert_array_equal(actual, np.asarray(expected[:length], dtype=float))
    # The next draw must also be identical: repeated bootstrap simulations
    # rely on consuming exactly the same deterministic RNG sequence.
    assert actual_rng.integers(0, 1_000_000) == reference_rng.integers(
        0, 1_000_000
    )

import numpy as np
import pandas as pd

from ai_trading.robustness import block_bootstrap_returns


def test_block_bootstrap_is_deterministic_with_seed() -> None:
    equity = pd.Series(100_000.0 * np.cumprod(1.0 + np.linspace(-0.002, 0.003, 120)))
    a = block_bootstrap_returns(equity, simulations=200, block_size=5, random_state=7)
    b = block_bootstrap_returns(equity, simulations=200, block_size=5, random_state=7)
    assert a == b
    assert 0.0 <= a.probability_positive <= 1.0
    assert a.p05_return <= a.median_return <= a.p95_return

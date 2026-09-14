import numpy as np
import pandas as pd

from ai_trading.portfolio import AllocationConfig, inverse_volatility_weights, target_notionals


def test_inverse_volatility_weights_are_capped_and_normalized() -> None:
    rng = np.random.default_rng(42)
    returns = pd.DataFrame(
        {
            "A": rng.normal(0, 0.01, 300),
            "B": rng.normal(0, 0.02, 300),
            "C": rng.normal(0, 0.03, 300),
        }
    )
    weights = inverse_volatility_weights(
        returns,
        AllocationConfig(max_asset_weight=0.60, target_gross_exposure=1.0),
    )
    assert abs(float(weights.sum()) - 1.0) < 1e-9
    assert float(weights.max()) <= 0.60 + 1e-9
    assert weights["A"] > weights["C"]

    notionals = target_notionals(100_000.0, weights)
    assert abs(float(notionals.sum()) - 100_000.0) < 1e-6

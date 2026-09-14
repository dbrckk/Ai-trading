import numpy as np
import pandas as pd

from ai_trading.portfolio import risk_parity_weights


def test_risk_parity_weights_are_bounded_and_normalized() -> None:
    rng = np.random.default_rng(5)
    base = rng.normal(0, 0.01, 400)
    returns = pd.DataFrame(
        {
            "A": base + rng.normal(0, 0.002, 400),
            "B": rng.normal(0, 0.015, 400),
            "C": rng.normal(0, 0.02, 400),
        }
    )
    weights = risk_parity_weights(
        returns,
        max_asset_weight=0.5,
        target_gross_exposure=1.0,
    )
    assert abs(float(weights.sum()) - 1.0) < 1e-9
    assert float(weights.max()) <= 0.5 + 1e-9
    assert (weights >= 0).all()

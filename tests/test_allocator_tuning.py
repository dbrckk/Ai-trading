import numpy as np
import pandas as pd

from ai_trading.allocator_tuning import tune_global_allocator


def test_allocator_tuning_returns_valid_config() -> None:
    rng = np.random.default_rng(21)
    columns = [
        "A|river|bull",
        "B|ensemble|range",
        "C|trend|bull",
    ]
    returns = pd.DataFrame(
        rng.normal(0.0004, 0.01, (220, len(columns))),
        columns=columns,
    )
    result = tune_global_allocator(
        returns,
        trials=2,
        folds=2,
        random_state=7,
    )
    assert result.trials == 2
    assert 0.90 <= result.best_config.cvar_alpha <= 0.99
    assert 0.0 < result.best_config.target_gross_exposure <= 1.0

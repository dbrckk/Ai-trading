import numpy as np
import pandas as pd

from ai_trading.global_allocator import (
    GlobalAllocatorConfig,
    allocate_global_capital,
    expected_shortfall,
)


def test_expected_shortfall_is_positive_for_lossy_tail() -> None:
    returns = pd.Series([0.01, 0.02, -0.03, -0.02, 0.005, -0.04])
    es = expected_shortfall(returns, alpha=0.8)
    assert es > 0.0


def test_global_allocator_respects_expert_caps_and_reports_turnover() -> None:
    rng = np.random.default_rng(7)
    cols = [
        "GC=F|river|bull",
        "GC=F|ensemble|bull",
        "SI=F|river|bull",
        "CL=F|river|bull",
    ]
    returns = pd.DataFrame(
        rng.normal(0.0005, 0.01, (300, len(cols))),
        columns=cols,
    )
    report = allocate_global_capital(
        returns,
        expected_alpha=pd.Series({c: 0.01 for c in cols}),
        quality=pd.Series({c: 0.8 for c in cols}),
        current_weights=pd.Series(0.0, index=cols),
        config=GlobalAllocatorConfig(
            max_expert_weight=0.35,
            max_asset_weight=0.50,
            max_turnover=2.0,
            max_cvar=0.20,
        ),
    )
    assert report.weights.max() <= 0.35 + 1e-9
    assert report.turnover >= 0.0
    assert report.cvar >= 0.0

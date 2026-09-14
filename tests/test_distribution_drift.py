import numpy as np
import pandas as pd

from ai_trading.drift import detect_distribution_drift
from ai_trading.features import FEATURES


def frame(seed: int, shift: float = 0.0, n: int = 300) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    return pd.DataFrame(
        {
            name: rng.normal(shift, 1.0, n)
            for name in FEATURES
        }
    )


def test_distribution_drift_detects_shifted_features() -> None:
    reference = frame(1, 0.0)
    recent = frame(2, 2.0, n=100)
    report = detect_distribution_drift(reference, recent)
    assert report.max_psi > 0.25
    assert report.retrain_requested
    assert report.risk_multiplier < 1.0


def test_distribution_drift_stays_low_for_similar_samples() -> None:
    reference = frame(3, 0.0)
    recent = reference.iloc[-100:].copy()
    report = detect_distribution_drift(reference, recent)
    assert report.risk_multiplier > 0.5

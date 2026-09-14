import numpy as np
import pandas as pd

from ai_trading.drift import detect_drift
from ai_trading.features import FEATURES


def frame(mean_shift: float, n: int) -> pd.DataFrame:
    rng = np.random.default_rng(7)
    return pd.DataFrame(
        {name: rng.normal(mean_shift, 1.0, n) for name in FEATURES}
    )


def test_detects_material_feature_drift() -> None:
    reference = frame(0.0, 200)
    recent = frame(3.0, 80)
    report = detect_drift(
        reference,
        recent,
        pd.Series(np.random.default_rng(1).normal(0, 1, 200)),
        pd.Series(np.random.default_rng(2).normal(0, 1, 80)),
    )
    assert report.drifted
    assert "feature distribution drift" in report.reasons


def test_no_drift_for_similar_distributions() -> None:
    rng = np.random.default_rng(11)
    reference = pd.DataFrame({name: rng.normal(0, 1, 200) for name in FEATURES})
    recent = pd.DataFrame({name: rng.normal(0, 1, 80) for name in FEATURES})
    report = detect_drift(
        reference,
        recent,
        pd.Series(rng.normal(0, 1, 200)),
        pd.Series(rng.normal(0, 1, 80)),
        feature_threshold=2.5,
        return_threshold=2.5,
    )
    assert not report.drifted

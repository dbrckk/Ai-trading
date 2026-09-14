import numpy as np
import pandas as pd

from ai_trading.data_quality import evaluate_market_data_quality


def clean_market(n: int = 120) -> pd.DataFrame:
    idx = pd.date_range("2026-01-01", periods=n, freq="D")
    close = 100.0 + np.arange(n, dtype=float) * 0.1
    return pd.DataFrame(
        {
            "Open": close - 0.02,
            "High": close + 0.05,
            "Low": close - 0.05,
            "Close": close,
        },
        index=idx,
    )


def test_clean_market_data_scores_high() -> None:
    report = evaluate_market_data_quality(clean_market())
    assert report.score >= 0.95
    assert report.valid


def test_invalid_ohlc_is_detected() -> None:
    df = clean_market()
    df.iloc[-1, df.columns.get_loc("High")] = 50.0
    report = evaluate_market_data_quality(df)
    assert report.ohlc_violation_fraction > 0.0
    assert not report.valid


def test_missing_required_column_fails_closed() -> None:
    report = evaluate_market_data_quality(clean_market().drop(columns=["Open"]))
    assert report.score == 0.0
    assert not report.valid

import numpy as np
import pandas as pd
import pytest

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



def intraday_market(n: int = 120) -> pd.DataFrame:
    frame = clean_market(n)
    frame.index = pd.date_range("2026-01-01", periods=n, freq="5min")
    return frame


def test_occasional_cadence_gap_is_tolerated() -> None:
    df = intraday_market().drop(index=intraday_market().index[50])

    report = evaluate_market_data_quality(df)

    assert 0.0 < report.gap_fraction <= 0.05
    assert "excessive cadence gaps" not in report.reasons
    assert report.valid


def test_repeated_cadence_gaps_fail_quality_gate() -> None:
    df = intraday_market()
    df = df.drop(index=df.index[10:110:10])

    report = evaluate_market_data_quality(df)

    assert report.gap_fraction > 0.05
    assert "excessive cadence gaps" in report.reasons
    assert not report.valid


def test_non_datetime_index_fails_cadence_quality() -> None:
    df = clean_market()
    df.index = pd.RangeIndex(len(df))

    report = evaluate_market_data_quality(df)

    assert report.gap_fraction == 1.0
    assert "excessive cadence gaps" in report.reasons
    assert not report.valid


@pytest.mark.parametrize(
    "kwargs",
    [
        {"lookback": 2},
        {"min_score": -0.1},
        {"min_score": 1.1},
    ],
)
def test_data_quality_rejects_invalid_scoring_configuration(kwargs) -> None:
    with pytest.raises(ValueError):
        evaluate_market_data_quality(clean_market(), **kwargs)



def test_single_session_break_in_recent_intraday_window_is_tolerated() -> None:
    df = intraday_market(120)
    before = df.iloc[:60].copy()
    after = df.iloc[60:].copy()
    after.index = after.index + pd.Timedelta(hours=8)
    session_split = pd.concat([before, after])

    report = evaluate_market_data_quality(session_split)

    assert 0.0 < report.gap_fraction <= 0.05
    assert "excessive cadence gaps" not in report.reasons
    assert report.valid

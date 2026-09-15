import pandas as pd

from ai_trading.dataset_evidence import build_dataset_evidence


def market() -> pd.DataFrame:
    index = pd.date_range("2025-01-01", periods=4, freq="D")
    return pd.DataFrame(
        {
            "Open": [100.0, 101.0, 102.0, 103.0],
            "High": [101.0, 102.0, 103.0, 104.0],
            "Low": [99.0, 100.0, 101.0, 102.0],
            "Close": [100.5, 101.5, 102.5, 103.5],
            "Volume": [1000.0, 1100.0, 1200.0, 1300.0],
        },
        index=index,
    )


def test_dataset_hash_is_deterministic() -> None:
    first = build_dataset_evidence(market())
    second = build_dataset_evidence(market())

    assert first == second
    assert len(first.data_hash) == 64
    assert first.rows == 4


def test_single_ohlcv_change_changes_dataset_hash() -> None:
    original = market()
    modified = original.copy()
    modified.iloc[2, modified.columns.get_loc("Close")] += 0.01

    assert (
        build_dataset_evidence(original).data_hash
        != build_dataset_evidence(modified).data_hash
    )


def test_timestamp_change_changes_dataset_hash() -> None:
    original = market()
    modified = original.copy()
    modified.index = modified.index + pd.Timedelta(hours=1)

    assert (
        build_dataset_evidence(original).data_hash
        != build_dataset_evidence(modified).data_hash
    )


def test_provenance_changes_evidence_identity() -> None:
    frame = market()
    first = build_dataset_evidence(
        frame,
        provider="yfinance",
        acquired_at_utc="2026-09-15T00:00:00+00:00",
    )
    second = build_dataset_evidence(
        frame,
        provider="alternate",
        acquired_at_utc="2026-09-15T00:00:00+00:00",
    )

    assert first.data_hash == second.data_hash
    assert first != second

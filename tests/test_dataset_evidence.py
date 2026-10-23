from datetime import UTC, datetime
from pathlib import Path

import pandas as pd
import pytest

from ai_trading.dataset_evidence import build_dataset_evidence
from ai_trading.prospective_capture import (
    collect_prospective_bars,
    prospective_snapshot,
)


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


def _prospective_sample() -> pd.DataFrame:
    dates = pd.date_range(
        "2026-10-25T23:55:00+00:00", periods=7, freq="5min"
    )
    return pd.DataFrame(
        {
            "Open": [100.0] * 7,
            "High": [101.0] * 7,
            "Low": [99.0] * 7,
            "Close": [100.0] * 7,
            "Volume": [5.0] * 7,
        },
        index=dates,
    )


def test_future_only_capture_excludes_prior_and_unclosed_bars() -> None:
    frame = _prospective_sample()
    cutoff = datetime(2026, 10, 26, tzinfo=UTC)
    acquired = datetime(2026, 10, 26, 0, 31, tzinfo=UTC)
    record = prospective_snapshot(
        frame, symbol="BTC-USD", cutoff_utc=cutoff,
        acquired_at_utc=acquired,
    )
    # Provider lag: entry 00:10 has closed at 00:15, and aged >= 15m.
    assert len(record["bars"]) == 3
    assert record["bars"][0][0] == "2026-10-26T00:00:00+00:00"
    assert record["bars"][-1][0] == "2026-10-26T00:10:00+00:00"
    assert record["dataset_evidence"]["rows"] == 3
    assert len(record["dataset_evidence"]["data_hash"]) == 64
    assert record["training_or_strategy_selection_performed"] is False
    assert record["trading_enabled"] is False

    changed = frame.copy()
    changed.loc[frame.index[2], "Close"] = 100.5
    second = prospective_snapshot(
        changed, symbol="BTC-USD", cutoff_utc=cutoff,
        acquired_at_utc=acquired,
    )
    assert (
        record["dataset_evidence"]["data_hash"]
        != second["dataset_evidence"]["data_hash"]
    )


def test_prospective_capture_rejects_invalid_clock_and_reordered_data() -> None:
    frame = _prospective_sample()
    cutoff = datetime(2026, 10, 26, tzinfo=UTC)
    acquired = datetime(2026, 10, 26, 0, 31, tzinfo=UTC)
    with pytest.raises(ValueError, match="timezone-aware"):
        prospective_snapshot(
            frame, symbol="GC=F", cutoff_utc=cutoff,
            acquired_at_utc=datetime(2026, 10, 26, 0, 31),
        )
    with pytest.raises(ValueError, match="ordered"):
        prospective_snapshot(
            frame.iloc[::-1], symbol="GC=F", cutoff_utc=cutoff,
            acquired_at_utc=acquired,
        )
    with pytest.raises(ValueError, match="timezone-aware"):
        prospective_snapshot(
            frame.tz_localize(None), symbol="GC=F", cutoff_utc=cutoff,
            acquired_at_utc=acquired,
        )


def test_pre_registered_capture_skips_provider_until_future_start(
    tmp_path, monkeypatch
) -> None:
    def forbid_network(*args, **kwargs):
        raise AssertionError("must not access market before registered start")

    monkeypatch.setattr(
        "ai_trading.prospective_capture.load_history", forbid_network
    )
    manifest = collect_prospective_bars(
        Path("research/mtf-prospective-2026-10-26-v1.json"),
        tmp_path,
        acquired_at_utc=datetime(2026, 10, 25, 23, tzinfo=UTC),
    )
    assert manifest["all_markets_acquired"] is False
    assert len(manifest["registration_sha256"]) == 64
    assert set(manifest["market_status"]) == {"GC=F", "^GDAXI", "BTC-USD"}
    assert set(manifest["market_status"].values()) == {
        "awaiting_future_completed_bars"
    }
    assert (tmp_path / "manifest.json").exists()
    assert list(tmp_path.glob("gold.json")) == []

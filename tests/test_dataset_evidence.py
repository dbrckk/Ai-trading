import json
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd
import pytest

from ai_trading.dataset_evidence import build_dataset_evidence
from ai_trading.prospective_capture import (
    collect_prospective_bars,
    prospective_snapshot,
    verify_capture_archive,
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


def test_prospective_registration_changes_are_rejected_before_download(
    tmp_path, monkeypatch
) -> None:
    original = Path("research/mtf-prospective-2026-10-26-v1.json")
    altered = tmp_path / "altered-registration.json"
    altered.write_text(
        original.read_text().replace(
            '"min_confidence": 0.56', '"min_confidence": 0.55'
        )
    )

    def forbid_network(*args, **kwargs):
        raise AssertionError("not allowed to query provider on manifest drift")

    monkeypatch.setattr(
        "ai_trading.prospective_capture.load_history", forbid_network
    )
    with pytest.raises(ValueError, match="registration hash mismatch"):
        collect_prospective_bars(
            altered, tmp_path / "captures",
            acquired_at_utc=datetime(2026, 10, 25, tzinfo=UTC),
        )



def test_prospective_capture_rejects_inconsistent_candles_and_off_grid_bars() -> None:
    cutoff = datetime(2026, 10, 26, tzinfo=UTC)
    acquired = datetime(2026, 10, 26, 0, 31, tzinfo=UTC)
    candle = _prospective_sample()
    invalid = candle.copy()
    invalid.loc[invalid.index[2], "High"] = 99.5
    with pytest.raises(ValueError, match="OHLC candle is inconsistent"):
        prospective_snapshot(
            invalid, symbol="GC=F", cutoff_utc=cutoff, acquired_at_utc=acquired
        )

    off_grid = candle.copy()
    off_grid.index = off_grid.index + pd.Timedelta(minutes=1)
    with pytest.raises(ValueError, match="off-grid"):
        prospective_snapshot(
            off_grid, symbol="GC=F", cutoff_utc=cutoff, acquired_at_utc=acquired
        )


def test_prospective_capture_does_not_claim_empty_market_was_acquired(
    tmp_path, monkeypatch
) -> None:
    sample = _prospective_sample()
    requested = []

    def provider(symbol, *, period, interval, max_attempts):
        assert (period, interval, max_attempts) == ("5d", "5m", 2)
        requested.append(symbol)
        return sample.iloc[:1].copy() if symbol == "^GDAXI" else sample.copy()

    monkeypatch.setattr("ai_trading.prospective_capture.load_history", provider)
    dest = tmp_path / "capture"
    manifest = collect_prospective_bars(
        Path("research/mtf-prospective-2026-10-26-v1.json"),
        dest,
        acquired_at_utc=datetime(2026, 10, 26, 0, 31, tzinfo=UTC),
    )
    assert requested == ["GC=F", "^GDAXI", "BTC-USD"]
    assert manifest["all_markets_acquired"] is False
    assert manifest["completed_market_count"] == 2
    dax = manifest["market_status"]["^GDAXI"]
    assert dax["status"] == "no_completed_bars"
    assert dax["rows"] == 0
    assert dax["dataset_sha256"] is None
    assert dax["file"] == "dax.json"
    assert len(dax["file_sha256"]) == 64
    assert manifest["market_status"]["GC=F"]["rows"] == 3
    assert len(manifest["market_status"]["BTC-USD"]["dataset_sha256"]) == 64
    assert (dest / "dax.json").exists()
    assert (dest / "manifest.json").exists()
    assert (dest / "dax.json").read_text().find('"bars": []') != -1


def test_prospective_capture_only_reports_success_with_three_hashed_future_markets(
    tmp_path, monkeypatch
) -> None:
    def provider(symbol, *, period, interval, max_attempts):
        assert symbol in {"GC=F", "^GDAXI", "BTC-USD"}
        return _prospective_sample()

    monkeypatch.setattr("ai_trading.prospective_capture.load_history", provider)
    manifest = collect_prospective_bars(
        Path("research/mtf-prospective-2026-10-26-v1.json"),
        tmp_path,
        acquired_at_utc=datetime(2026, 10, 26, 0, 31, tzinfo=UTC),
    )
    assert manifest["all_markets_acquired"] is True
    assert manifest["completed_market_count"] == 3
    for item in manifest["market_status"].values():
        assert item["status"] == "completed_bars_captured"
        assert item["rows"] == 3
        assert len(item["dataset_sha256"]) == 64


def test_prospective_archive_verification_detects_tampering(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "ai_trading.prospective_capture.load_history",
        lambda symbol, **kwargs: _prospective_sample(),
    )
    collect_prospective_bars(
        Path("research/mtf-prospective-2026-10-26-v1.json"),
        tmp_path,
        acquired_at_utc=datetime(2026, 10, 26, 0, 31, tzinfo=UTC),
    )
    verify_capture_archive(tmp_path)
    path = tmp_path / "gold.json"
    path.write_text(path.read_text() + " ", encoding="utf-8")
    with pytest.raises(ValueError, match="file hash mismatch"):
        verify_capture_archive(tmp_path)



def test_prospective_archive_recomputes_data_evidence_even_if_file_hash_rewritten(
    tmp_path, monkeypatch
) -> None:
    from hashlib import sha256

    monkeypatch.setattr(
        "ai_trading.prospective_capture.load_history",
        lambda symbol, **kwargs: _prospective_sample(),
    )
    collect_prospective_bars(
        Path("research/mtf-prospective-2026-10-26-v1.json"),
        tmp_path,
        acquired_at_utc=datetime(2026, 10, 26, 0, 31, tzinfo=UTC),
    )
    verify_capture_archive(tmp_path)

    path = tmp_path / "gold.json"
    snapshot = json.loads(path.read_text(encoding="utf-8"))
    snapshot["bars"][0][4] = 100.5  # plausible changed Close, old evidence
    path.write_text(json.dumps(snapshot), encoding="utf-8")
    manifest_path = tmp_path / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["market_status"]["GC=F"]["file_sha256"] = sha256(
        path.read_bytes()
    ).hexdigest()
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(ValueError, match="independent OHLCV evidence mismatch"):
        verify_capture_archive(tmp_path)


def test_prospective_archive_rejects_precutoff_bar_even_with_rehashed_file(
    tmp_path, monkeypatch
) -> None:
    from hashlib import sha256

    monkeypatch.setattr(
        "ai_trading.prospective_capture.load_history",
        lambda symbol, **kwargs: _prospective_sample(),
    )
    collect_prospective_bars(
        Path("research/mtf-prospective-2026-10-26-v1.json"),
        tmp_path,
        acquired_at_utc=datetime(2026, 10, 26, 0, 31, tzinfo=UTC),
    )
    path = tmp_path / "btc.json"
    snapshot = json.loads(path.read_text(encoding="utf-8"))
    snapshot["bars"][0][0] = "2026-10-25T23:55:00+00:00"
    path.write_text(json.dumps(snapshot), encoding="utf-8")
    manifest_path = tmp_path / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["market_status"]["BTC-USD"]["file_sha256"] = sha256(
        path.read_bytes()
    ).hexdigest()
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(ValueError, match="independent OHLCV evidence mismatch"):
        verify_capture_archive(tmp_path)


def test_prospective_archive_requires_frozen_registration_hash(
    tmp_path, monkeypatch
) -> None:
    monkeypatch.setattr(
        "ai_trading.prospective_capture.load_history",
        lambda symbol, **kwargs: _prospective_sample(),
    )
    collect_prospective_bars(
        Path("research/mtf-prospective-2026-10-26-v1.json"),
        tmp_path,
        acquired_at_utc=datetime(2026, 10, 26, 0, 31, tzinfo=UTC),
    )
    manifest_path = tmp_path / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["registration_sha256"] = "0" * 64
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(ValueError, match="registration or study identity"):
        verify_capture_archive(tmp_path)

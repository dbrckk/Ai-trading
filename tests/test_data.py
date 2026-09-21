import numpy as np
import pandas as pd
import pytest

import ai_trading.data as data_module


def test_load_history_keeps_price_rows_when_volume_is_missing(monkeypatch) -> None:
    index = pd.date_range("2026-09-18 08:00", periods=60, freq="5min")
    frame = pd.DataFrame(
        {
            "Open": np.linspace(23000.0, 23100.0, len(index)),
            "High": np.linspace(23010.0, 23110.0, len(index)),
            "Low": np.linspace(22990.0, 23090.0, len(index)),
            "Close": np.linspace(23005.0, 23105.0, len(index)),
            "Volume": np.nan,
        },
        index=index,
    )
    monkeypatch.setattr(data_module.yf, "download", lambda *args, **kwargs: frame)

    loaded = data_module.load_history("^GDAXI", period="5d", interval="5m")

    assert len(loaded) == len(frame)
    assert loaded["Volume"].eq(0.0).all()
    assert loaded[["Open", "High", "Low", "Close"]].notna().all().all()


def test_load_history_retries_transient_provider_failure(monkeypatch) -> None:
    index = pd.date_range("2026-09-18 08:00", periods=3, freq="5min")
    frame = pd.DataFrame(
        {
            "Open": [100.0, 101.0, 102.0],
            "High": [101.0, 102.0, 103.0],
            "Low": [99.0, 100.0, 101.0],
            "Close": [100.5, 101.5, 102.5],
            "Volume": [10.0, 11.0, 12.0],
        },
        index=index,
    )
    calls = {"count": 0}

    def flaky_download(*args, **kwargs):
        calls["count"] += 1
        if calls["count"] == 1:
            raise RuntimeError("temporary provider failure")
        return frame

    monkeypatch.setattr(data_module.yf, "download", flaky_download)
    monkeypatch.setattr(data_module, "sleep", lambda *_args, **_kwargs: None)

    loaded = data_module.load_history(
        "GC=F",
        period="5d",
        interval="5m",
        max_attempts=2,
    )

    assert calls["count"] == 2
    assert len(loaded) == 3


def test_load_history_sorts_and_deduplicates_provider_rows(monkeypatch) -> None:
    index = pd.to_datetime(
        ["2026-09-18 08:10", "2026-09-18 08:05", "2026-09-18 08:05"]
    )
    frame = pd.DataFrame(
        {
            "Open": [102.0, 100.0, 101.0],
            "High": [103.0, 101.0, 102.0],
            "Low": [101.0, 99.0, 100.0],
            "Close": [102.5, 100.5, 101.5],
            "Volume": [12.0, 10.0, 11.0],
        },
        index=index,
    )
    monkeypatch.setattr(data_module.yf, "download", lambda *args, **kwargs: frame)

    loaded = data_module.load_history("GC=F", max_attempts=1)

    assert loaded.index.is_monotonic_increasing
    assert not loaded.index.has_duplicates
    assert loaded.iloc[0]["Close"] == 101.5


def test_load_history_rejects_inconsistent_ohlc(monkeypatch) -> None:
    index = pd.date_range("2026-09-18 08:00", periods=2, freq="5min")
    frame = pd.DataFrame(
        {
            "Open": [100.0, 101.0],
            "High": [99.0, 102.0],
            "Low": [98.0, 100.0],
            "Close": [100.5, 101.5],
            "Volume": [10.0, 11.0],
        },
        index=index,
    )
    monkeypatch.setattr(data_module.yf, "download", lambda *args, **kwargs: frame)

    with pytest.raises(ValueError, match="Failed to load valid market data"):
        data_module.load_history("GC=F", max_attempts=1)

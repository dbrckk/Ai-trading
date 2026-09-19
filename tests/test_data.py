import numpy as np
import pandas as pd

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

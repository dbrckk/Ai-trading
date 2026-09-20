from __future__ import annotations

import numpy as np
import pandas as pd

from ai_trading.mtf_parameter_benchmark import (
    MTFBenchmarkConfig,
    benchmark_payload,
    evaluate_market_config,
    run_parameter_benchmark,
)


def sample_market(n: int = 3200, phase: float = 0.0) -> pd.DataFrame:
    idx = pd.date_range("2026-01-01", periods=n, freq="5min")
    t = np.arange(n, dtype=float)
    close = (
        100.0
        + 0.005 * t
        + 1.7 * np.sin(t / 17.0 + phase)
        + 0.8 * np.sin(t / 71.0 + phase / 2.0)
    )
    open_ = close * (1.0 + 0.0004 * np.sin(t / 9.0 + phase))
    return pd.DataFrame(
        {
            "Open": open_,
            "High": np.maximum(open_, close) * 1.003,
            "Low": np.minimum(open_, close) * 0.997,
            "Close": close,
            "Volume": 1000.0 + (t % 80) * 4.0,
        },
        index=idx,
    )


def test_market_benchmark_is_purged_and_reports_directional_evidence() -> None:
    config = MTFBenchmarkConfig(
        horizon_bars=3,
        minimum_threshold=0.001,
        atr_multiplier=0.25,
        max_train_rows=700,
    )

    result = evaluate_market_config(
        "TEST",
        sample_market(),
        config,
        folds=2,
        test_window_bars=24,
        min_train_rows=500,
    )

    assert result.symbol == "TEST"
    assert result.config_name == config.name
    assert result.folds == 2
    assert result.observations == 48
    assert 0 <= result.directional_observations <= result.observations
    assert (
        result.long_labels + result.flat_labels + result.short_labels
        == result.observations
    )
    assert 0.0 <= result.accuracy <= 1.0
    assert 0.0 <= result.macro_recall <= 1.0
    assert 0.0 <= result.brier <= 1.0
    assert 0.0 <= result.selection_score <= 1.0


def test_parameter_benchmark_ranks_configs_across_markets() -> None:
    markets = {
        "A": sample_market(phase=0.0),
        "B": sample_market(phase=0.7),
    }
    configs = (
        MTFBenchmarkConfig(2, 0.001, 0.15, 600),
        MTFBenchmarkConfig(3, 0.001, 0.25, 700),
    )

    results = run_parameter_benchmark(
        markets,
        configs,
        folds=1,
        test_window_bars=20,
        min_train_rows=500,
    )

    assert len(results) == 2
    assert results[0].aggregate_score >= results[1].aggregate_score
    assert all(len(result.markets) == 2 for result in results)
    assert all(result.total_observations == 40 for result in results)


def test_benchmark_payload_is_reproducible_and_explicit() -> None:
    markets = {"A": sample_market()}
    configs = (MTFBenchmarkConfig(3, 0.001, 0.25, 600),)
    results = run_parameter_benchmark(
        markets,
        configs,
        folds=1,
        test_window_bars=20,
        min_train_rows=500,
    )

    payload = benchmark_payload(results)

    assert payload["method"]["execution_timeframe"] == "5m"
    assert payload["method"]["context_timeframes"] == ["5m", "15m", "1h", "4h"]
    assert payload["method"]["walk_forward"] is True
    assert payload["method"]["purged"] is True
    assert payload["ranking"][0]["rank"] == 1
    assert payload["ranking"][0]["config"]["horizon_bars"] == 3

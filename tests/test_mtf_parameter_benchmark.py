from __future__ import annotations

import numpy as np
import pandas as pd

from ai_trading.mtf_parameter_benchmark import (
    MTFBenchmarkMetrics,
    MTFBenchmarkResult,
    MTFBenchmarkScenario,
    benchmark_scenario,
    summarize_results,
)


def sample_market(n: int = 1800) -> pd.DataFrame:
    idx = pd.date_range("2026-01-01", periods=n, freq="5min")
    t = np.arange(n, dtype=float)
    close = 100.0 + 0.012 * t + 1.8 * np.sin(t / 17.0) + 0.8 * np.sin(t / 5.0)
    open_ = close * (1.0 + 0.0004 * np.sin(t / 9.0))
    return pd.DataFrame(
        {
            "Open": open_,
            "High": np.maximum(open_, close) * 1.002,
            "Low": np.minimum(open_, close) * 0.998,
            "Close": close,
            "Volume": 1000.0 + (t % 80) * 4.0,
        },
        index=idx,
    )


def test_benchmark_scenario_produces_purged_out_of_sample_metrics() -> None:
    result = benchmark_scenario(
        sample_market(),
        symbol="TEST",
        scenario=MTFBenchmarkScenario(
            "test",
            horizon_bars=3,
            minimum_threshold=0.0005,
            atr_multiplier=0.15,
            max_train_rows=700,
        ),
        folds=2,
        min_train_rows=500,
        test_points_per_fold=18,
    )

    assert result.symbol == "TEST"
    assert result.folds == 2
    assert result.metrics.observations >= 10
    assert 0.0 <= result.metrics.accuracy <= 1.0
    assert 0.0 <= result.metrics.directional_label_rate <= 1.0
    assert 0.0 <= result.metrics.active_prediction_rate <= 1.0
    assert np.isfinite(result.metrics.mean_net_bps)


def _result(
    name: str,
    *,
    mean_net_bps: float,
    quality: float,
    hit: float,
    directional_rate: float,
    active_rate: float,
) -> MTFBenchmarkResult:
    scenario = MTFBenchmarkScenario(name, 3, 0.0005, 0.15)
    return MTFBenchmarkResult(
        symbol="A",
        scenario=scenario,
        folds=3,
        metrics=MTFBenchmarkMetrics(
            observations=100,
            directional_labels=int(100 * directional_rate),
            active_predictions=int(100 * active_rate),
            accuracy=0.6,
            quality_score=quality,
            directional_hit_rate=hit,
            directional_label_rate=directional_rate,
            active_prediction_rate=active_rate,
            mean_net_bps=mean_net_bps,
            median_net_bps=mean_net_bps,
        ),
    )


def test_summary_penalizes_flat_only_and_negative_market_profiles() -> None:
    robust = _result(
        "robust",
        mean_net_bps=4.0,
        quality=0.70,
        hit=0.62,
        directional_rate=0.35,
        active_rate=0.30,
    )
    flat = _result(
        "flat",
        mean_net_bps=0.0,
        quality=0.95,
        hit=0.0,
        directional_rate=0.0,
        active_rate=0.0,
    )

    summaries = summarize_results((flat, robust))

    assert summaries[0].scenario.name == "robust"
    assert summaries[0].objective > summaries[1].objective

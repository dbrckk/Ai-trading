from __future__ import annotations

import numpy as np
import pandas as pd

import ai_trading.mtf_parameter_benchmark as benchmark_module
from ai_trading.mtf_parameter_benchmark import (
    MarketBenchmarkResult,
    MTFBenchmarkConfig,
    benchmark_payload,
    btc_focused_benchmark_grid,
    evaluate_market_config,
    market_selections,
    robustness_benchmark_grid,
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
        min_confidence=0.56,
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
    assert 0 <= result.active_predictions <= result.observations
    assert 0.0 <= result.active_precision <= 1.0


def test_parameter_benchmark_ranks_configs_across_markets() -> None:
    markets = {
        "A": sample_market(phase=0.0),
        "B": sample_market(phase=0.7),
    }
    configs = (
        MTFBenchmarkConfig(2, 0.001, 0.15, 600, 0.56),
        MTFBenchmarkConfig(3, 0.001, 0.25, 700, 0.60),
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
    configs = (MTFBenchmarkConfig(3, 0.001, 0.25, 600, 0.56),)
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
    assert payload["method"]["common_random_seed"] is True
    assert payload["method"]["directional_gate"] == {
        "min_active_predictions": 20,
        "min_active_precision": 0.5,
    }
    assert payload["ranking"][0]["rank"] == 1
    assert payload["ranking"][0]["config"]["horizon_bars"] == 3
    assert payload["ranking"][0]["config"]["min_confidence"] == 0.56



def test_btc_focused_grid_is_bounded_and_longer_horizon() -> None:
    grid = btc_focused_benchmark_grid()

    assert len(grid) == 36
    assert {config.horizon_minutes for config in grid} == {45, 60, 90}
    assert {config.max_train_rows for config in grid} == {1000}
    assert {config.atr_multiplier for config in grid} == {0.15, 0.25}
    assert {config.min_confidence for config in grid} == {0.56, 0.60}


def test_market_selections_choose_gate_passing_config_per_symbol() -> None:
    markets = {
        "A": sample_market(phase=0.0),
        "B": sample_market(phase=0.9),
    }
    configs = (
        MTFBenchmarkConfig(3, 0.0005, 0.25, 700, 0.50),
        MTFBenchmarkConfig(6, 0.0005, 0.25, 700, 0.50),
    )
    results = run_parameter_benchmark(
        markets,
        configs,
        folds=1,
        test_window_bars=24,
        min_train_rows=500,
    )

    selections = market_selections(results)

    assert set(selections) == {"A", "B"}
    for selection in selections.values():
        if selection is not None:
            assert selection["active_predictions"] >= 20
            assert selection["active_precision"] > 0.5
            assert selection["config_name"]


def test_payload_exposes_per_market_selection() -> None:
    markets = {"A": sample_market()}
    configs = (MTFBenchmarkConfig(3, 0.0005, 0.25, 700, 0.50),)
    results = run_parameter_benchmark(
        markets,
        configs,
        folds=1,
        test_window_bars=24,
        min_train_rows=500,
    )

    payload = benchmark_payload(results)

    assert "market_selections" in payload
    assert set(payload["market_selections"]) == {"A"}



def test_parameter_grid_uses_same_random_seed_for_every_config(monkeypatch) -> None:
    seen_random_states: list[int] = []

    def fake_evaluate_market_config(
        symbol,
        market,
        config,
        *,
        folds,
        test_window_bars,
        min_train_rows,
        random_state,
    ):
        del market, folds, test_window_bars, min_train_rows
        seen_random_states.append(random_state)
        return MarketBenchmarkResult(
            symbol=symbol,
            config_name=config.name,
            folds=1,
            observations=20,
            directional_observations=12,
            long_labels=6,
            flat_labels=8,
            short_labels=6,
            accuracy=0.5,
            macro_recall=0.5,
            brier=0.25,
            directional_accuracy=0.5,
            directional_edge=0.0,
            active_predictions=20,
            active_precision=0.55,
            quality_score=0.5,
            selection_score=0.5,
            directional_gate_passed=True,
        )

    monkeypatch.setattr(
        benchmark_module,
        "evaluate_market_config",
        fake_evaluate_market_config,
    )

    configs = (
        MTFBenchmarkConfig(3, 0.0005, 0.25, 700, 0.56),
        MTFBenchmarkConfig(9, 0.0005, 0.25, 700, 0.60),
    )
    run_parameter_benchmark(
        {"A": sample_market(), "B": sample_market(phase=0.3)},
        configs,
        folds=1,
        test_window_bars=20,
        min_train_rows=500,
        random_state=73,
    )

    assert seen_random_states == [73, 73, 73, 73]



def test_robustness_grid_is_compact_and_contains_validated_candidates() -> None:
    grid = robustness_benchmark_grid()

    assert len(grid) == 12
    names = {config.name for config in grid}
    assert "h45m-min5bp-atr0.25-train1000-conf56" in names
    assert "h45m-min5bp-atr0.25-train1000-conf60" in names
    assert "h90m-min3bp-atr0.15-train1000-conf60" in names
    assert {config.max_train_rows for config in grid} == {1000}
    assert {config.horizon_minutes for config in grid} == {45, 90}

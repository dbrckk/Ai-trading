from __future__ import annotations

from dataclasses import replace
from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest

import ai_trading.mtf_parameter_benchmark as benchmark_module
from ai_trading.mtf_parameter_benchmark import (
    AggregateBenchmarkResult,
    MarketBenchmarkResult,
    MTFBenchmarkConfig,
    MTFResearchTrade,
    benchmark_payload,
    btc_focused_benchmark_grid,
    economic_cost_stress_report,
    evaluate_market_config,
    market_selections,
    run_chronological_holdout,
    run_parameter_benchmark,
    summarize_economic_trade_quality,
)
from ai_trading.mtf_shared_portfolio import simulate_shared_mtf_portfolio
from ai_trading.research_history import frozen_preprospective_history


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
    assert 0 <= result.economic_trades <= result.active_predictions
    assert len(result.paper_trades) == result.economic_trades
    assert np.isfinite(result.economic_compounded_net_return)
    assert np.isfinite(result.sized_equity_final)
    assert result.sized_equity_final > 0.0
    assert result.sized_net_return == pytest.approx(
        result.sized_equity_final / 100_000.0 - 1.0
    )
    assert 0.0 <= result.sized_max_drawdown < 1.0
    assert result.economic_trade_quality is not None
    quality = result.economic_trade_quality
    assert (
        quality.winning_trades + quality.losing_trades + quality.flat_trades
        == result.economic_trades
    )
    if quality.win_rate_all_trades is not None:
        assert 0.0 <= quality.win_rate_all_trades <= 1.0
    assert quality.net_profit_factor is None or quality.net_profit_factor >= 0.0


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

    # Explicitly empty search grids must fail rather than expand silently to
    # the expensive default 36-configuration sweep.
    with pytest.raises(ValueError, match="configs must not be empty"):
        run_parameter_benchmark(markets, configs=())


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
    assert payload["method"]["economic_gate"]["min_non_overlapping_trades"] == 20
    assert payload["method"]["economic_gate"]["win_rate_diagnostics"] == (
        "descriptive_after_round_trip_costs_only"
    )
    # A deceptively high hit rate is not enough when losing trades cost more.
    outcomes = summarize_economic_trade_quality([0.02, 0.01, -0.04, 0.0])
    assert outcomes.winning_trades == 2
    assert outcomes.losing_trades == 1
    assert outcomes.flat_trades == 1
    assert outcomes.win_rate_all_trades == pytest.approx(0.5)
    assert outcomes.decisive_win_rate == pytest.approx(2 / 3)
    assert outcomes.decisive_win_rate_lower95 < outcomes.break_even_decisive_win_rate
    assert outcomes.decisive_win_rate_upper95 > outcomes.decisive_win_rate_lower95
    assert outcomes.mean_win_net_return == pytest.approx(0.015)
    assert outcomes.mean_loss_abs_net_return == pytest.approx(0.04)
    assert outcomes.payoff_ratio == pytest.approx(0.375)
    assert outcomes.break_even_decisive_win_rate == pytest.approx(0.04 / 0.055)
    assert outcomes.net_profit_factor == pytest.approx(0.75)
    assert summarize_economic_trade_quality([]).win_rate_all_trades is None
    assert summarize_economic_trade_quality([0.0]).flat_trades == 1
    assert summarize_economic_trade_quality([0.01]).net_profit_factor is None
    with pytest.raises(ValueError, match="finite"):
        summarize_economic_trade_quality([float("nan")])
    assert payload["method"]["economic_gate"]["transaction_cost_bps"] == 2.0
    assert payload["method"]["economic_gate"]["slippage_bps"] == 1.0
    assert payload["method"]["economic_gate"]["no_auto_promotion"] is True
    sized = payload["method"]["economic_gate"]["sized_research_account"]
    assert sized["starting_cash"] == 100_000.0
    assert sized["position_fraction"] == 0.10
    assert sized["multi_market_aggregation"] is False
    assert sized["funding_borrow_margin_modeled"] is False
    assert payload["ranking"][0]["rank"] == 1
    assert payload["ranking"][0]["config"]["horizon_bars"] == 3
    assert payload["ranking"][0]["config"]["min_confidence"] == 0.56
    # A rolling Yahoo period must not put any prospective bars into the
    # historical parameter selection, even when downloaded successfully.
    earlier = sample_market(n=5).tz_localize("UTC")
    future = earlier.iloc[-1:].copy()
    future.index = pd.DatetimeIndex(["2026-10-26T00:00:00Z"])
    combined = pd.concat([earlier, future])
    allowed = frozen_preprospective_history(combined, symbol="GC=F")
    assert allowed.index.equals(earlier.index)
    with pytest.raises(ValueError, match="timezone-aware"):
        frozen_preprospective_history(combined.tz_localize(None), symbol="GC=F")
    with pytest.raises(ValueError, match="no verifiable pre-prospective"):
        frozen_preprospective_history(future, symbol="GC=F")

    stress = payload["ranking"][0]["markets"][0]["economic_cost_stress"]
    assert stress["scope"] == "retrospective_same_fills_hypothetical_no_promotion"
    assert stress["stress_is_not_a_selection_gate"] is True
    assert tuple(stress["scenarios"]) == ("1x", "2x", "3x")




def test_btc_focused_grid_is_bounded_and_longer_horizon() -> None:
    grid = btc_focused_benchmark_grid()

    assert len(grid) == 36
    assert {config.horizon_minutes for config in grid} == {45, 60, 90}
    assert {config.max_train_rows for config in grid} == {1000}
    assert {config.atr_multiplier for config in grid} == {0.15, 0.25}
    assert {config.min_confidence for config in grid} == {0.56, 0.60}

    for invalid in (np.nan, np.inf, -np.inf):
        with pytest.raises(ValueError, match="minimum_threshold"):
            MTFBenchmarkConfig(3, invalid, 0.25, 700, 0.56)
        with pytest.raises(ValueError, match="atr_multiplier"):
            MTFBenchmarkConfig(3, 0.001, invalid, 700, 0.56)


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
        transaction_cost_bps,
        slippage_bps,
    ):
        del market, folds, test_window_bars, min_train_rows
        assert transaction_cost_bps == 2.0
        assert slippage_bps == 1.0
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


def test_cost_aware_mtf_gate_rejects_directional_wins_erased_by_fees(monkeypatch) -> None:
    """Only disjoint completed trades count toward economic eligibility."""

    class AlwaysLongModel:
        def __init__(self, **kwargs):
            del kwargs

        def fit(self, rows, labels):
            assert len(rows) == len(labels)
            return self

        def predict_one(self, row, regime):
            del row, regime
            return SimpleNamespace(side=1, confidence=0.99)

    monkeypatch.setattr(benchmark_module, "EnsembleDirectionModel", AlwaysLongModel)

    # Direction is known in this controlled benchmark, but the next-open
    # realized edge is small enough for realistic costs to erase it.
    market = sample_market()
    trend = 100.0 + np.arange(len(market), dtype=float) * 0.05
    market["Open"] = trend
    market["Close"] = trend
    market["High"] = trend * 1.0002
    market["Low"] = trend * 0.9998
    config = MTFBenchmarkConfig(3, 0.0005, 0.25, 700, 0.50)

    without_costs = evaluate_market_config(
        "TEST", market, config,
        folds=2, test_window_bars=96, min_train_rows=500,
        transaction_cost_bps=0.0, slippage_bps=0.0,
    )
    with_costs = evaluate_market_config(
        "TEST", market, config,
        folds=2, test_window_bars=96, min_train_rows=500,
        transaction_cost_bps=100.0, slippage_bps=50.0,
    )

    assert without_costs.economic_trades >= 20
    assert without_costs.economic_trades < without_costs.active_predictions
    assert without_costs.economic_compounded_net_return > 0.0
    assert without_costs.sized_net_return > 0.0
    assert without_costs.sized_equity_final > 100_000.0
    assert without_costs.sized_max_drawdown >= 0.0
    assert without_costs.economic_gate_passed is True
    assert with_costs.directional_gate_passed is True
    assert with_costs.economic_mean_net_return < 0.0
    assert with_costs.economic_compounded_net_return < 0.0
    assert with_costs.sized_net_return < 0.0
    assert with_costs.sized_equity_final < 100_000.0
    assert with_costs.sized_max_drawdown > 0.0
    assert with_costs.economic_gate_passed is False
    stressed = economic_cost_stress_report(with_costs)["scenarios"]
    assert stressed["1x"]["compounded_net_return"] == pytest.approx(
        with_costs.economic_compounded_net_return
    )
    assert stressed["1x"]["trades"] == with_costs.economic_trades
    assert stressed["1x"]["assumed_round_trip_cost_bps"] == pytest.approx(300.0)
    assert (
        stressed["3x"]["compounded_net_return"]
        <= stressed["2x"]["compounded_net_return"]
        <= stressed["1x"]["compounded_net_return"]
    )


    result = AggregateBenchmarkResult(
        config=config, markets=(without_costs,),
        mean_selection_score=without_costs.selection_score,
        stability_penalty=0.0,
        aggregate_score=without_costs.selection_score,
        total_observations=without_costs.observations,
        total_directional_observations=without_costs.directional_observations,
        markets_passing_directional_gate=1,
    )
    assert market_selections((result,))["TEST"] is not None
    assert market_selections((replace(result, markets=(with_costs,)),))["TEST"] is None

    # Same frozen settings, but selection only sees the pre-holdout prefix.
    # The final chronological slice is evaluated *after* validation picks
    # a candidate, and its results cannot change the chosen hyperparameters.
    study = run_chronological_holdout(
        {"TEST": market},
        (config,),
        holdout_bars=160,
        validation_folds=2,
        validation_test_window_bars=96,
        min_train_rows=500,
        transaction_cost_bps=0.0,
        slippage_bps=0.0,
    )
    cutoff = market.index[-160]
    assert study["cutoffs"]["TEST"]["holdout_start"] == cutoff.isoformat()
    assert study["cutoffs"]["TEST"]["validation_end"] == market.index[-161].isoformat()
    assert study["validation"]["market_selections"]["TEST"]["config_name"] == config.name
    assert study["holdout"]["TEST"]["status"] == "passed_for_manual_review"
    assert study["holdout"]["TEST"]["result"]["economic_trades"] >= 20
    assert study["holdout"]["TEST"]["result"]["sized_net_return"] > 0.0
    assert study["method"]["previously_unseen_across_research_runs"] is False
    assert study["method"]["auto_promote"] is False

    # A losing validation cannot be revived by peeking at holdout outcomes.
    blocked = run_chronological_holdout(
        {"TEST": market},
        (config,),
        holdout_bars=160,
        validation_folds=2,
        validation_test_window_bars=96,
        min_train_rows=500,
        transaction_cost_bps=100.0,
        slippage_bps=50.0,
    )
    assert blocked["validation"]["market_selections"]["TEST"] is None
    assert blocked["holdout"]["TEST"]["status"] == (
        "not_evaluated_no_validation_candidate"
    )
    assert blocked["holdout"]["TEST"]["result"] is None


def test_shared_mtf_account_reconciles_overlapping_markets_and_costs() -> None:
    """Replay a long and short concurrently on one constrained cash account."""
    times = pd.date_range("2026-10-01", periods=5, freq="5min")
    market_a = pd.DataFrame(
        {"Open": [100.0] * 5, "Close": [100., 101., 102., 103., 104.]},
        index=times,
    )
    market_b = pd.DataFrame(
        {"Open": [50.0] * 5, "Close": [50., 49., 48., 47., 46.]},
        index=times,
    )
    # Use a benchmark-produced result so all other metadata is real, then
    # replace only the controlled execution evidence for a deterministic
    # shared-capital accounting check.
    base = evaluate_market_config(
        "A", sample_market(),
        MTFBenchmarkConfig(3, 0.0005, 0.25, 700, 0.50),
        folds=1, test_window_bars=24, min_train_rows=500,
    )
    a = replace(
        base, symbol="A", economic_trades=1,
        paper_trades=(MTFResearchTrade(
            times[1].isoformat(), times[3].isoformat(), 100.0, 103.0, 1
        ),),
    )
    b = replace(
        base, symbol="B", economic_trades=1,
        paper_trades=(MTFResearchTrade(
            times[1].isoformat(), times[3].isoformat(), 50.0, 47.0, -1
        ),),
    )
    account = simulate_shared_mtf_portfolio(
        {"A": market_a, "B": market_b}, (a, b),
        starting_cash=100_000.0, per_market_fraction=0.1, max_gross_fraction=0.15,
    )
    assert account.accepted_trades == 2
    assert account.rejected_entries == 0
    assert account.max_concurrent_positions == 2
    assert account.final_equity > 100_000
    assert account.total_costs > 0
    assert account.final_equity - 100_000 == pytest.approx(account.realized_net_pnl)
    assert account.net_return == pytest.approx(account.final_equity / 100_000 - 1)
    assert account.max_drawdown >= 0
    assert len(account.equity_by_timestamp) == 5
    assert sum(
        abs(fill["units"] * fill["price"])
        for fill in account.fills if fill["action"] == "entry"
    ) <= 15_000
    assert [fill["action"] for fill in account.fills] == [
        "entry", "entry", "exit", "exit"
    ]

    high_cost = simulate_shared_mtf_portfolio(
        {"A": market_a, "B": market_b},
        (replace(a, transaction_cost_bps=500.0, slippage_bps=0),
         replace(b, transaction_cost_bps=500.0, slippage_bps=0)),
        max_gross_fraction=0.15,
    )
    assert high_cost.final_equity < 100_000
    assert high_cost.max_drawdown > 0
    assert high_cost.total_costs > account.total_costs
    with pytest.raises(ValueError, match="incomplete"):
        simulate_shared_mtf_portfolio(
            {"A": market_a, "B": market_b}, (replace(a, paper_trades=()), b)
        )

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd

from .data import load_history
from .ensemble import EnsembleDirectionModel
from .model_quality import evaluate_model_quality
from .multi_timeframe_features import (
    MTF_CHALLENGER_FEATURES,
    make_multi_timeframe_challenger_features,
    make_volatility_adaptive_labels,
)
from .regime import detect_regime

DEFAULT_SYMBOLS = ("GC=F", "^GDAXI", "BTC-USD")


@dataclass(frozen=True)
class MTFBenchmarkScenario:
    name: str
    horizon_bars: int
    minimum_threshold: float
    atr_multiplier: float
    max_train_rows: int = 2000
    min_confidence: float = 0.56


@dataclass(frozen=True)
class MTFBenchmarkMetrics:
    observations: int
    directional_labels: int
    active_predictions: int
    accuracy: float
    quality_score: float
    directional_hit_rate: float
    directional_label_rate: float
    active_prediction_rate: float
    mean_net_bps: float
    median_net_bps: float


@dataclass(frozen=True)
class MTFBenchmarkResult:
    symbol: str
    scenario: MTFBenchmarkScenario
    metrics: MTFBenchmarkMetrics
    folds: int


@dataclass(frozen=True)
class MTFBenchmarkSummary:
    scenario: MTFBenchmarkScenario
    markets: int
    observations: int
    directional_labels: int
    mean_quality_score: float
    mean_directional_hit_rate: float
    mean_directional_label_rate: float
    mean_active_prediction_rate: float
    mean_net_bps: float
    worst_market_net_bps: float
    objective: float


DEFAULT_SCENARIOS = tuple(
    MTFBenchmarkScenario(
        f"10m_conservative_t{train_rows}_c{int(confidence * 100)}",
        2,
        0.0010,
        0.40,
        train_rows,
        confidence,
    )
    for train_rows in (750, 1000, 1500, 2000)
    for confidence in (0.56, 0.60, 0.65)
)


def _evaluation_index(index: pd.DatetimeIndex) -> pd.DatetimeIndex:
    return index[index.minute % 15 == 0]


def _future_returns(market: pd.DataFrame, horizon_bars: int) -> pd.Series:
    close = market["Close"].astype(float)
    return close.shift(-horizon_bars) / close - 1.0


def _fold_starts(
    evaluation_index: pd.DatetimeIndex,
    *,
    folds: int,
    test_points_per_fold: int,
) -> tuple[int, ...]:
    if folds < 1:
        raise ValueError("folds must be positive")
    if test_points_per_fold < 5:
        raise ValueError("test_points_per_fold must be at least 5")
    usable = len(evaluation_index) - test_points_per_fold
    if usable < 1:
        return ()
    return tuple(
        int(usable * fraction)
        for fraction in np.linspace(0.0, 1.0, folds)
    )


def benchmark_scenario(
    market: pd.DataFrame,
    *,
    symbol: str,
    scenario: MTFBenchmarkScenario,
    folds: int = 3,
    min_train_rows: int = 500,
    test_points_per_fold: int = 96,
    round_trip_cost_bps: float = 6.0,
) -> MTFBenchmarkResult:
    features = make_multi_timeframe_challenger_features(market)
    labels = make_volatility_adaptive_labels(
        market,
        horizon_bars=scenario.horizon_bars,
        minimum_threshold=scenario.minimum_threshold,
        atr_multiplier=scenario.atr_multiplier,
    )
    future_returns = _future_returns(market, scenario.horizon_bars)

    valid = (
        features.dropna()
        .index.intersection(labels.dropna().index)
        .intersection(future_returns.dropna().index)
    )
    evaluation_index = valid.intersection(_evaluation_index(valid))
    purge = max(1, scenario.horizon_bars)
    evaluation_index = pd.DatetimeIndex(
        [
            idx
            for idx in evaluation_index
            if int(valid.get_loc(idx)) >= min_train_rows + purge
        ]
    )
    starts = _fold_starts(
        evaluation_index,
        folds=folds,
        test_points_per_fold=test_points_per_fold,
    )
    if not starts:
        raise ValueError(f"insufficient usable MTF history for {symbol}")

    predictions: list[int] = []
    raw_predictions: list[int] = []
    confidences: list[float] = []
    realized: list[int] = []
    net_bps: list[float] = []
    completed_folds = 0

    for fold_no, start in enumerate(starts):
        test_idx = evaluation_index[start : start + test_points_per_fold]
        if len(test_idx) < 5:
            continue
        first_test = test_idx[0]
        train_end = int(valid.get_loc(first_test)) - purge
        train_start = max(0, train_end - scenario.max_train_rows)
        train_idx = valid[train_start:train_end]
        if len(train_idx) < min_train_rows:
            continue

        model = EnsembleDirectionModel(
            random_state=42 + fold_no,
            feature_names=MTF_CHALLENGER_FEATURES,
        )
        model.fit(features.loc[train_idx], labels.loc[train_idx])
        completed_folds += 1

        for signal_idx in test_idx:
            row = features.loc[signal_idx, MTF_CHALLENGER_FEATURES]
            prediction = model.predict_one(row, detect_regime(row))
            label = int(labels.loc[signal_idx])
            raw_side = int(prediction.side)
            side = raw_side if prediction.confidence >= scenario.min_confidence else 0
            predictions.append(side)
            raw_predictions.append(raw_side)
            confidences.append(float(prediction.confidence))
            realized.append(label)

            gross_bps = float(side * future_returns.loc[signal_idx] * 10_000.0)
            cost_bps = round_trip_cost_bps if side != 0 else 0.0
            net_bps.append(gross_bps - cost_bps)

    if len(predictions) < 5:
        raise ValueError(f"benchmark produced insufficient observations for {symbol}")

    index = pd.RangeIndex(len(predictions))
    pred_series = pd.Series(predictions, index=index, dtype="int64")
    raw_pred_series = pd.Series(raw_predictions, index=index, dtype="int64")
    confidence_series = pd.Series(confidences, index=index, dtype="float64")
    label_series = pd.Series(realized, index=index, dtype="int64")
    quality = evaluate_model_quality(raw_pred_series, confidence_series, label_series)

    directional_mask = label_series != 0
    active_mask = pred_series != 0
    directional_hit = (
        float((pred_series[directional_mask] == label_series[directional_mask]).mean())
        if directional_mask.any()
        else 0.0
    )

    metrics = MTFBenchmarkMetrics(
        observations=len(predictions),
        directional_labels=int(directional_mask.sum()),
        active_predictions=int(active_mask.sum()),
        accuracy=float((pred_series == label_series).mean()),
        quality_score=float(quality.score),
        directional_hit_rate=directional_hit,
        directional_label_rate=float(directional_mask.mean()),
        active_prediction_rate=float(active_mask.mean()),
        mean_net_bps=float(np.mean(net_bps)),
        median_net_bps=float(np.median(net_bps)),
    )
    return MTFBenchmarkResult(
        symbol=symbol,
        scenario=scenario,
        metrics=metrics,
        folds=completed_folds,
    )


def summarize_results(
    results: Iterable[MTFBenchmarkResult],
) -> tuple[MTFBenchmarkSummary, ...]:
    grouped: dict[str, list[MTFBenchmarkResult]] = {}
    for result in results:
        grouped.setdefault(result.scenario.name, []).append(result)

    summaries: list[MTFBenchmarkSummary] = []
    for rows in grouped.values():
        scenario = rows[0].scenario
        metrics = [row.metrics for row in rows]
        mean_quality = float(np.mean([item.quality_score for item in metrics]))
        mean_hit = float(np.mean([item.directional_hit_rate for item in metrics]))
        mean_label_rate = float(np.mean([item.directional_label_rate for item in metrics]))
        mean_active_rate = float(np.mean([item.active_prediction_rate for item in metrics]))
        mean_net = float(np.mean([item.mean_net_bps for item in metrics]))
        worst_net = float(min(item.mean_net_bps for item in metrics))

        flat_penalty = max(0.0, 0.15 - mean_label_rate) * 2.0
        inactivity_penalty = max(0.0, 0.10 - mean_active_rate) * 2.0
        negative_market_penalty = max(0.0, -worst_net) / 25.0
        objective = (
            mean_quality
            + 0.30 * mean_hit
            + 0.01 * mean_net
            - flat_penalty
            - inactivity_penalty
            - negative_market_penalty
        )
        summaries.append(
            MTFBenchmarkSummary(
                scenario=scenario,
                markets=len(rows),
                observations=sum(item.observations for item in metrics),
                directional_labels=sum(item.directional_labels for item in metrics),
                mean_quality_score=mean_quality,
                mean_directional_hit_rate=mean_hit,
                mean_directional_label_rate=mean_label_rate,
                mean_active_prediction_rate=mean_active_rate,
                mean_net_bps=mean_net,
                worst_market_net_bps=worst_net,
                objective=float(objective),
            )
        )

    return tuple(sorted(summaries, key=lambda item: item.objective, reverse=True))


def run_benchmark(
    *,
    symbols: tuple[str, ...] = DEFAULT_SYMBOLS,
    scenarios: tuple[MTFBenchmarkScenario, ...] = DEFAULT_SCENARIOS,
    period: str = "1mo",
    interval: str = "5m",
) -> tuple[tuple[MTFBenchmarkResult, ...], tuple[MTFBenchmarkSummary, ...]]:
    results: list[MTFBenchmarkResult] = []
    for symbol in symbols:
        market = load_history(symbol, period, interval)
        for scenario in scenarios:
            results.append(
                benchmark_scenario(
                    market,
                    symbol=symbol,
                    scenario=scenario,
                )
            )
    rows = tuple(results)
    return rows, summarize_results(rows)


def save_benchmark(
    path: str | Path,
    results: tuple[MTFBenchmarkResult, ...],
    summaries: tuple[MTFBenchmarkSummary, ...],
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "results": [
            {
                "symbol": row.symbol,
                "scenario": asdict(row.scenario),
                "metrics": asdict(row.metrics),
                "folds": row.folds,
            }
            for row in results
        ],
        "summaries": [
            {
                "scenario": asdict(row.scenario),
                **{key: value for key, value in asdict(row).items() if key != "scenario"},
            }
            for row in summaries
        ],
    }
    target.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def main() -> None:
    results, summaries = run_benchmark()
    save_benchmark("artifacts/mtf-parameter-benchmark.json", results, summaries)
    print(json.dumps([asdict(item) for item in summaries], indent=2, default=str))


if __name__ == "__main__":
    main()

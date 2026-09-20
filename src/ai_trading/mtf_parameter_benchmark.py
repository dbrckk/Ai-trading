from __future__ import annotations

import argparse
import json
from collections.abc import Iterable
from dataclasses import asdict, dataclass
from pathlib import Path
from statistics import fmean, pstdev

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


@dataclass(frozen=True)
class MTFBenchmarkConfig:
    horizon_bars: int
    minimum_threshold: float
    atr_multiplier: float
    max_train_rows: int

    @property
    def horizon_minutes(self) -> int:
        return self.horizon_bars * 5

    @property
    def name(self) -> str:
        threshold_bps = round(self.minimum_threshold * 10_000)
        return (
            f"h{self.horizon_minutes}m"
            f"-min{threshold_bps}bp"
            f"-atr{self.atr_multiplier:g}"
            f"-train{self.max_train_rows}"
        )


@dataclass(frozen=True)
class MarketBenchmarkResult:
    symbol: str
    config_name: str
    folds: int
    observations: int
    directional_observations: int
    long_labels: int
    flat_labels: int
    short_labels: int
    accuracy: float
    macro_recall: float
    brier: float
    directional_accuracy: float
    directional_edge: float
    quality_score: float
    selection_score: float


@dataclass(frozen=True)
class AggregateBenchmarkResult:
    config: MTFBenchmarkConfig
    markets: tuple[MarketBenchmarkResult, ...]
    mean_selection_score: float
    stability_penalty: float
    aggregate_score: float
    total_observations: int
    total_directional_observations: int


def default_benchmark_grid() -> tuple[MTFBenchmarkConfig, ...]:
    return tuple(
        MTFBenchmarkConfig(
            horizon_bars=horizon,
            minimum_threshold=0.001,
            atr_multiplier=atr_multiplier,
            max_train_rows=max_train_rows,
        )
        for horizon in (2, 3, 6)
        for atr_multiplier in (0.15, 0.25, 0.40)
        for max_train_rows in (1000, 2000)
    )


def _macro_recall(predicted: pd.Series, realized: pd.Series) -> float:
    recalls: list[float] = []
    for label in (-1, 0, 1):
        mask = realized == label
        if not bool(mask.any()):
            continue
        recalls.append(float((predicted.loc[mask] == label).mean()))
    return fmean(recalls) if recalls else 0.0


def _selection_score(
    *,
    macro_recall: float,
    directional_accuracy: float,
    brier: float,
    quality_score: float,
    directional_observations: int,
) -> float:
    directional_evidence = min(1.0, directional_observations / 20.0)
    return float(
        0.30 * macro_recall
        + 0.25 * directional_accuracy
        + 0.20 * max(0.0, 1.0 - brier)
        + 0.15 * quality_score
        + 0.10 * directional_evidence
    )


def _fold_test_windows(
    usable: pd.DatetimeIndex,
    *,
    folds: int,
    test_window_bars: int,
    min_train_rows: int,
) -> tuple[pd.DatetimeIndex, ...]:
    if folds < 1:
        raise ValueError("folds must be at least 1")
    if test_window_bars < 5:
        raise ValueError("test_window_bars must be at least 5")

    required = min_train_rows + folds * test_window_bars
    if len(usable) < required:
        raise ValueError(
            f"need at least {required} usable rows, got {len(usable)}"
        )

    start = len(usable) - folds * test_window_bars
    return tuple(
        usable[
            start + fold * test_window_bars :
            start + (fold + 1) * test_window_bars
        ]
        for fold in range(folds)
    )


def evaluate_market_config(
    symbol: str,
    market: pd.DataFrame,
    config: MTFBenchmarkConfig,
    *,
    folds: int = 2,
    test_window_bars: int = 48,
    min_train_rows: int = 500,
    random_state: int = 42,
) -> MarketBenchmarkResult:
    if config.max_train_rows < min_train_rows:
        raise ValueError("max_train_rows must be >= min_train_rows")

    features = make_multi_timeframe_challenger_features(market)
    labels = make_volatility_adaptive_labels(
        market,
        horizon_bars=config.horizon_bars,
        minimum_threshold=config.minimum_threshold,
        atr_multiplier=config.atr_multiplier,
    )
    usable = features.dropna().index.intersection(labels.dropna().index)
    windows = _fold_test_windows(
        usable,
        folds=folds,
        test_window_bars=test_window_bars,
        min_train_rows=min_train_rows,
    )

    market_positions = {timestamp: pos for pos, timestamp in enumerate(market.index)}
    predicted_sides: list[int] = []
    confidences: list[float] = []
    realized_labels: list[int] = []

    completed_folds = 0
    for fold, test_idx in enumerate(windows):
        first_test = test_idx[0]
        first_test_pos = market_positions[first_test]
        max_train_pos = first_test_pos - config.horizon_bars
        train_candidates = [
            idx
            for idx in usable
            if market_positions[idx] <= max_train_pos
        ]
        if len(train_candidates) < min_train_rows:
            continue
        train_idx = train_candidates[-config.max_train_rows :]

        model = EnsembleDirectionModel(
            random_state=random_state + fold,
            feature_names=MTF_CHALLENGER_FEATURES,
        )
        model.fit(
            features.loc[train_idx, MTF_CHALLENGER_FEATURES],
            labels.loc[train_idx],
        )
        completed_folds += 1

        for signal_idx in test_idx:
            row = features.loc[signal_idx, MTF_CHALLENGER_FEATURES]
            prediction = model.predict_one(row, detect_regime(row))
            label = labels.loc[signal_idx]
            if pd.isna(label):
                continue
            predicted_sides.append(int(prediction.side))
            confidences.append(float(prediction.confidence))
            realized_labels.append(int(label))

    if completed_folds == 0 or len(realized_labels) < 5:
        raise ValueError("benchmark produced insufficient out-of-sample evidence")

    index = pd.RangeIndex(len(realized_labels))
    predicted = pd.Series(predicted_sides, index=index, dtype="int64")
    confidence = pd.Series(confidences, index=index, dtype="float64")
    realized = pd.Series(realized_labels, index=index, dtype="int64")

    quality = evaluate_model_quality(predicted, confidence, realized)
    directional_mask = realized != 0
    directional_observations = int(directional_mask.sum())
    directional_accuracy = (
        float((predicted.loc[directional_mask] == realized.loc[directional_mask]).mean())
        if directional_observations
        else 0.0
    )
    macro_recall = _macro_recall(predicted, realized)
    selection_score = _selection_score(
        macro_recall=macro_recall,
        directional_accuracy=directional_accuracy,
        brier=quality.brier,
        quality_score=quality.score,
        directional_observations=directional_observations,
    )

    return MarketBenchmarkResult(
        symbol=symbol,
        config_name=config.name,
        folds=completed_folds,
        observations=len(realized_labels),
        directional_observations=directional_observations,
        long_labels=int((realized == 1).sum()),
        flat_labels=int((realized == 0).sum()),
        short_labels=int((realized == -1).sum()),
        accuracy=float(quality.accuracy),
        macro_recall=float(macro_recall),
        brier=float(quality.brier),
        directional_accuracy=float(directional_accuracy),
        directional_edge=float(quality.directional_edge),
        quality_score=float(quality.score),
        selection_score=float(selection_score),
    )


def run_parameter_benchmark(
    markets: dict[str, pd.DataFrame],
    configs: Iterable[MTFBenchmarkConfig] | None = None,
    *,
    folds: int = 2,
    test_window_bars: int = 48,
    min_train_rows: int = 500,
) -> tuple[AggregateBenchmarkResult, ...]:
    grid = tuple(configs or default_benchmark_grid())
    if not markets:
        raise ValueError("markets must not be empty")
    if not grid:
        raise ValueError("configs must not be empty")

    results: list[AggregateBenchmarkResult] = []
    for config_index, config in enumerate(grid):
        market_results = tuple(
            evaluate_market_config(
                symbol,
                market,
                config,
                folds=folds,
                test_window_bars=test_window_bars,
                min_train_rows=min_train_rows,
                random_state=42 + config_index * 100,
            )
            for symbol, market in markets.items()
        )
        scores = [row.selection_score for row in market_results]
        stability_penalty = pstdev(scores) if len(scores) > 1 else 0.0
        mean_score = fmean(scores)
        results.append(
            AggregateBenchmarkResult(
                config=config,
                markets=market_results,
                mean_selection_score=float(mean_score),
                stability_penalty=float(stability_penalty),
                aggregate_score=float(mean_score - 0.10 * stability_penalty),
                total_observations=sum(row.observations for row in market_results),
                total_directional_observations=sum(
                    row.directional_observations for row in market_results
                ),
            )
        )

    return tuple(
        sorted(
            results,
            key=lambda result: (
                result.aggregate_score,
                result.total_directional_observations,
            ),
            reverse=True,
        )
    )


def benchmark_payload(results: tuple[AggregateBenchmarkResult, ...]) -> dict[str, object]:
    return {
        "method": {
            "execution_timeframe": "5m",
            "context_timeframes": ["5m", "15m", "1h", "4h"],
            "walk_forward": True,
            "purged": True,
            "selection_score": (
                "30% macro recall + 25% directional accuracy + "
                "20% calibration + 15% model quality + 10% directional evidence; "
                "minus 10% cross-market score dispersion"
            ),
        },
        "ranking": [
            {
                "rank": rank,
                "config": asdict(result.config),
                "config_name": result.config.name,
                "aggregate_score": result.aggregate_score,
                "mean_selection_score": result.mean_selection_score,
                "stability_penalty": result.stability_penalty,
                "total_observations": result.total_observations,
                "total_directional_observations": result.total_directional_observations,
                "markets": [asdict(row) for row in result.markets],
            }
            for rank, result in enumerate(results, start=1)
        ],
    }


def write_benchmark_report(
    results: tuple[AggregateBenchmarkResult, ...],
    *,
    json_path: str | Path,
    markdown_path: str | Path,
) -> None:
    payload = benchmark_payload(results)
    json_target = Path(json_path)
    markdown_target = Path(markdown_path)
    json_target.parent.mkdir(parents=True, exist_ok=True)
    markdown_target.parent.mkdir(parents=True, exist_ok=True)
    json_target.write_text(
        json.dumps(payload, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    lines = [
        "# MTF parameter benchmark",
        "",
        "Leakage-safe purged walk-forward comparison across markets.",
        "",
        "| Rank | Config | Score | Directional / total |",
        "| ---: | --- | ---: | ---: |",
    ]
    for rank, result in enumerate(results, start=1):
        lines.append(
            f"| {rank} | {result.config.name} | "
            f"{result.aggregate_score:.4f} | "
            f"{result.total_directional_observations} / {result.total_observations} |"
        )
    lines.extend(["", "## Per-market detail", ""])
    for rank, result in enumerate(results, start=1):
        lines.append(f"### {rank}. {result.config.name}")
        lines.append("")
        lines.append(
            "| Market | Sel. score | Macro recall | Directional accuracy | "
            "Brier | L/F/S |"
        )
        lines.append("| --- | ---: | ---: | ---: | ---: | ---: |")
        for row in result.markets:
            lines.append(
                f"| {row.symbol} | {row.selection_score:.4f} | "
                f"{row.macro_recall:.3f} | {row.directional_accuracy:.3f} | "
                f"{row.brier:.3f} | "
                f"{row.long_labels}/{row.flat_labels}/{row.short_labels} |"
            )
        lines.append("")
    markdown_target.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run MTF parameter benchmark")
    parser.add_argument("--symbols", default="GC=F,^GDAXI,BTC-USD")
    parser.add_argument("--period", default="1mo")
    parser.add_argument("--interval", default="5m")
    parser.add_argument("--folds", type=int, default=2)
    parser.add_argument("--test-window-bars", type=int, default=48)
    parser.add_argument(
        "--json-output",
        default="artifacts/mtf_benchmark/results.json",
    )
    parser.add_argument(
        "--markdown-output",
        default="artifacts/mtf_benchmark/report.md",
    )
    args = parser.parse_args()

    symbols = tuple(part.strip() for part in args.symbols.split(",") if part.strip())
    if not symbols:
        raise SystemExit("provide at least one symbol")

    markets = {
        symbol: load_history(symbol, args.period, args.interval)
        for symbol in symbols
    }
    results = run_parameter_benchmark(
        markets,
        folds=args.folds,
        test_window_bars=args.test_window_bars,
    )
    write_benchmark_report(
        results,
        json_path=args.json_output,
        markdown_path=args.markdown_output,
    )

    print(json.dumps(benchmark_payload(results), sort_keys=True))


if __name__ == "__main__":
    main()

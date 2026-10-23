from __future__ import annotations

import argparse
import json
from collections.abc import Iterable
from dataclasses import asdict, dataclass
from pathlib import Path
from math import isfinite, prod
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

_MIN_ACTIVE_PREDICTIONS = 20
_MIN_ACTIVE_PRECISION = 0.50
_MIN_ECONOMIC_TRADES = 20
_DEFAULT_TRANSACTION_COST_BPS = 2.0
_DEFAULT_SLIPPAGE_BPS = 1.0


@dataclass(frozen=True)
class MTFBenchmarkConfig:
    horizon_bars: int
    minimum_threshold: float
    atr_multiplier: float
    max_train_rows: int
    min_confidence: float

    def __post_init__(self) -> None:
        if self.horizon_bars < 1:
            raise ValueError("horizon_bars must be at least 1")
        if self.minimum_threshold < 0:
            raise ValueError("minimum_threshold must be non-negative")
        if self.atr_multiplier < 0:
            raise ValueError("atr_multiplier must be non-negative")
        if self.max_train_rows < 1:
            raise ValueError("max_train_rows must be at least 1")
        if not 0.0 <= self.min_confidence <= 1.0:
            raise ValueError("min_confidence must be in [0, 1]")

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
            f"-conf{round(self.min_confidence * 100)}"
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
    active_predictions: int
    active_precision: float
    quality_score: float
    selection_score: float
    directional_gate_passed: bool
    # Independent, non-overlapping next-open to horizon-close paper trades.
    # These are not portfolio returns and do not change the hosted runtime.
    economic_trades: int = 0
    economic_mean_net_return: float = 0.0
    economic_compounded_net_return: float = 0.0
    economic_gate_passed: bool = False
    transaction_cost_bps: float = _DEFAULT_TRANSACTION_COST_BPS
    slippage_bps: float = _DEFAULT_SLIPPAGE_BPS


@dataclass(frozen=True)
class AggregateBenchmarkResult:
    config: MTFBenchmarkConfig
    markets: tuple[MarketBenchmarkResult, ...]
    mean_selection_score: float
    stability_penalty: float
    aggregate_score: float
    total_observations: int
    total_directional_observations: int
    markets_passing_directional_gate: int


def default_benchmark_grid() -> tuple[MTFBenchmarkConfig, ...]:
    """Refined grid after the first coarse 10m/15m/30m benchmark.

    The first run showed 30m ahead of 15m/10m, while ATR multipliers were
    largely masked by the 10bp threshold floor. This grid therefore expands
    horizon and confidence while testing a lower threshold floor.
    """

    return tuple(
        MTFBenchmarkConfig(
            horizon_bars=horizon,
            minimum_threshold=minimum_threshold,
            atr_multiplier=0.25,
            max_train_rows=max_train_rows,
            min_confidence=min_confidence,
        )
        for horizon in (3, 6, 9)
        for minimum_threshold in (0.0005, 0.001)
        for max_train_rows in (1000, 2000)
        for min_confidence in (0.56, 0.60, 0.65)
    )


def btc_focused_benchmark_grid() -> tuple[MTFBenchmarkConfig, ...]:
    """Focused search for BTC after the shared grid failed its directional gate."""

    return tuple(
        MTFBenchmarkConfig(
            horizon_bars=horizon,
            minimum_threshold=minimum_threshold,
            atr_multiplier=atr_multiplier,
            max_train_rows=1000,
            min_confidence=min_confidence,
        )
        for horizon in (9, 12, 18)
        for minimum_threshold in (0.0003, 0.0004, 0.0005)
        for atr_multiplier in (0.15, 0.25)
        for min_confidence in (0.56, 0.60)
    )


def market_selections(
    results: tuple[AggregateBenchmarkResult, ...],
) -> dict[str, dict[str, object] | None]:
    """Choose the strongest gate-passing configuration independently per market."""

    symbols = sorted(
        {
            row.symbol
            for aggregate in results
            for row in aggregate.markets
        }
    )
    selections: dict[str, dict[str, object] | None] = {}
    for symbol in symbols:
        candidates: list[tuple[MarketBenchmarkResult, MTFBenchmarkConfig]] = []
        for aggregate in results:
            for row in aggregate.markets:
                if (
                    row.symbol == symbol
                    and row.directional_gate_passed
                    and row.economic_gate_passed
                ):
                    candidates.append((row, aggregate.config))
        if not candidates:
            selections[symbol] = None
            continue
        row, config = max(
            candidates,
            key=lambda item: (
                item[0].selection_score,
                item[0].active_precision,
                item[0].active_predictions,
                -item[0].brier,
            ),
        )
        selections[symbol] = {
            "config_name": row.config_name,
            "config": asdict(config),
            "selection_score": row.selection_score,
            "active_precision": row.active_precision,
            "active_predictions": row.active_predictions,
            "economic_trades": row.economic_trades,
            "economic_compounded_net_return": row.economic_compounded_net_return,
            "directional_accuracy": row.directional_accuracy,
            "macro_recall": row.macro_recall,
            "brier": row.brier,
        }
    return selections


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
    active_precision: float,
    active_predictions: int,
) -> float:
    active_edge = max(0.0, min(1.0, (active_precision - 0.5) * 2.0))
    active_evidence = min(1.0, active_predictions / 20.0)
    return float(
        0.35 * active_edge
        + 0.25 * macro_recall
        + 0.15 * directional_accuracy
        + 0.15 * max(0.0, 1.0 - brier)
        + 0.10 * active_evidence
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
    transaction_cost_bps: float = _DEFAULT_TRANSACTION_COST_BPS,
    slippage_bps: float = _DEFAULT_SLIPPAGE_BPS,
) -> MarketBenchmarkResult:
    if any(
        not isfinite(cost) or cost < 0.0
        for cost in (transaction_cost_bps, slippage_bps)
    ):
        raise ValueError("execution costs must be finite and non-negative")
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
    economic_returns: list[float] = []
    last_economic_exit_pos = -1
    round_trip_cost = 2.0 * (transaction_cost_bps + slippage_bps) / 10_000.0

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
            effective_side = (
                int(prediction.side)
                if float(prediction.confidence) >= config.min_confidence
                else 0
            )
            predicted_sides.append(effective_side)
            confidences.append(float(prediction.confidence))
            realized_labels.append(int(label))

            # Economic audit uses non-overlapping executions. Counting all
            # overlapping horizon predictions as separate trades would
            # exaggerate turnover, statistical evidence and possible profit.
            signal_pos = market_positions[signal_idx]
            if effective_side and signal_pos > last_economic_exit_pos:
                entry_open = float(market["Open"].iloc[signal_pos + 1])
                exit_close = float(
                    market["Close"].iloc[signal_pos + config.horizon_bars]
                )
                if (
                    not isfinite(entry_open) or entry_open <= 0.0
                    or not isfinite(exit_close) or exit_close <= 0.0
                ):
                    raise ValueError("invalid prices for next-open economic audit")
                net_return = (
                    effective_side * (exit_close / entry_open - 1.0)
                    - round_trip_cost
                )
                if not isfinite(net_return):
                    raise ValueError("invalid net return for economic audit")
                economic_returns.append(net_return)
                last_economic_exit_pos = signal_pos + config.horizon_bars

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
    active_mask = predicted != 0
    active_predictions = int(active_mask.sum())
    active_precision = (
        float((predicted.loc[active_mask] == realized.loc[active_mask]).mean())
        if active_predictions
        else 0.0
    )
    macro_recall = _macro_recall(predicted, realized)
    selection_score = _selection_score(
        macro_recall=macro_recall,
        directional_accuracy=directional_accuracy,
        brier=quality.brier,
        active_precision=active_precision,
        active_predictions=active_predictions,
    )
    directional_gate_passed = (
        active_predictions >= _MIN_ACTIVE_PREDICTIONS
        and active_precision > _MIN_ACTIVE_PRECISION
    )
    economic_mean = fmean(economic_returns) if economic_returns else 0.0
    # A loss exceeding available capital is conservatively treated as ruin.
    economic_growth = prod(max(0.0, 1.0 + ret) for ret in economic_returns)
    if not isfinite(economic_growth):
        raise ValueError("non-finite compounded economic return")
    economic_net = float(economic_growth - 1.0)
    economic_gate_passed = (
        len(economic_returns) >= _MIN_ECONOMIC_TRADES
        and economic_mean > 0.0
        and economic_net > 0.0
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
        active_predictions=active_predictions,
        active_precision=float(active_precision),
        quality_score=float(quality.score),
        selection_score=float(selection_score),
        directional_gate_passed=directional_gate_passed,
        economic_trades=len(economic_returns),
        economic_mean_net_return=float(economic_mean),
        economic_compounded_net_return=economic_net,
        economic_gate_passed=economic_gate_passed,
        transaction_cost_bps=transaction_cost_bps,
        slippage_bps=slippage_bps,
    )


def run_parameter_benchmark(
    markets: dict[str, pd.DataFrame],
    configs: Iterable[MTFBenchmarkConfig] | None = None,
    *,
    folds: int = 2,
    test_window_bars: int = 48,
    min_train_rows: int = 500,
    random_state: int = 42,
    transaction_cost_bps: float = _DEFAULT_TRANSACTION_COST_BPS,
    slippage_bps: float = _DEFAULT_SLIPPAGE_BPS,
) -> tuple[AggregateBenchmarkResult, ...]:
    grid = tuple(configs or default_benchmark_grid())
    if not markets:
        raise ValueError("markets must not be empty")
    if not grid:
        raise ValueError("configs must not be empty")

    results: list[AggregateBenchmarkResult] = []
    for config in grid:
        market_results = tuple(
            evaluate_market_config(
                symbol,
                market,
                config,
                folds=folds,
                test_window_bars=test_window_bars,
                min_train_rows=min_train_rows,
                random_state=random_state,
                transaction_cost_bps=transaction_cost_bps,
                slippage_bps=slippage_bps,
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
                markets_passing_directional_gate=sum(
                    1 for row in market_results if row.directional_gate_passed
                ),
            )
        )

    return tuple(
        sorted(
            results,
            key=lambda result: (
                result.markets_passing_directional_gate,
                result.aggregate_score,
                result.total_directional_observations,
            ),
            reverse=True,
        )
    )


def benchmark_payload(results: tuple[AggregateBenchmarkResult, ...]) -> dict[str, object]:
    cost_reference = results[0].markets[0] if results and results[0].markets else None
    return {
        "method": {
            "execution_timeframe": "5m",
            "context_timeframes": ["5m", "15m", "1h", "4h"],
            "walk_forward": True,
            "purged": True,
            "common_random_seed": True,
            "directional_gate": {
                "min_active_predictions": _MIN_ACTIVE_PREDICTIONS,
                "min_active_precision": _MIN_ACTIVE_PRECISION,
            },
            "economic_gate": {
                "min_non_overlapping_trades": _MIN_ECONOMIC_TRADES,
                "requires_positive_mean_net_return": True,
                "requires_positive_compounded_net_return": True,
                "entry": "next_bar_open",
                "exit": "horizon_bar_close",
                "round_trip_cost_sides": 2,
                "transaction_cost_bps": (
                    cost_reference.transaction_cost_bps if cost_reference else None
                ),
                "slippage_bps": cost_reference.slippage_bps if cost_reference else None,
                "not_portfolio_pnl": True,
                "no_auto_promotion": True,
            },
            "selection_score": (
                "35% positive active-direction edge + 25% macro recall + "
                "15% realized directional accuracy + 15% calibration + "
                "10% active-signal evidence; minus 10% cross-market dispersion"
            ),
        },
        "market_selections": market_selections(results),
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
                "markets_passing_directional_gate": (
                    result.markets_passing_directional_gate
                ),
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

    selections = market_selections(results)
    lines = [
        "# MTF parameter benchmark",
        "",
        "Purged walk-forward directional and cost-aware research; not live PnL.",
        "Economic audit uses independent next-open entries, horizon-close exits,",
        "two-sided modeled fees and slippage, and does not simulate a portfolio.",
        "",
        "## Best validated configuration per market",
        "",
    ]
    for symbol, selection in selections.items():
        if selection is None:
            lines.append(
                f"- **{symbol}**: no configuration passed both the directional "
                "and positive-net-cost gates."
            )
        else:
            lines.append(
                f"- **{symbol}**: `{selection['config_name']}` "
                f"(active precision {float(selection['active_precision']):.1%}, "
                f"n={int(selection['active_predictions'])}; "
                f"independent net return "
                f"{float(selection['economic_compounded_net_return']):+.2%}, "
                f"n={int(selection['economic_trades'])})."
            )
    lines.extend(
        [
            "",
            "| Rank | Config | Score | Directional / total | Markets gate |",
            "| ---: | --- | ---: | ---: | ---: |",
        ]
    )
    for rank, result in enumerate(results, start=1):
        lines.append(
            f"| {rank} | {result.config.name} | "
            f"{result.aggregate_score:.4f} | "
            f"{result.total_directional_observations} / {result.total_observations} | "
            f"{result.markets_passing_directional_gate} / {len(result.markets)} |"
        )
    lines.extend(["", "## Per-market detail", ""])
    for rank, result in enumerate(results, start=1):
        lines.append(f"### {rank}. {result.config.name}")
        lines.append("")
        lines.append(
            "| Market | Sel. score | Macro recall | Directional accuracy | "
            "Active precision | Active n | Net return | Net n | Cost gate | Brier | L/F/S |"
        )
        lines.append(
            "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | ---: | ---: |"
        )
        for row in result.markets:
            lines.append(
                f"| {row.symbol} | {row.selection_score:.4f} | "
                f"{row.macro_recall:.3f} | {row.directional_accuracy:.3f} | "
                f"{row.active_precision:.3f} | {row.active_predictions} | "
                f"{row.economic_compounded_net_return:+.2%} | "
                f"{row.economic_trades} | "
                f"{'PASS' if row.economic_gate_passed else 'FAIL'} | "
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
    parser.add_argument(
        "--profile",
        choices=("global", "btc-focused"),
        default="global",
    )
    parser.add_argument("--test-window-bars", type=int, default=48)
    parser.add_argument(
        "--transaction-cost-bps", type=float, default=_DEFAULT_TRANSACTION_COST_BPS
    )
    parser.add_argument(
        "--slippage-bps", type=float, default=_DEFAULT_SLIPPAGE_BPS
    )
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
    configs = (
        btc_focused_benchmark_grid()
        if args.profile == "btc-focused"
        else default_benchmark_grid()
    )
    results = run_parameter_benchmark(
        markets,
        configs=configs,
        folds=args.folds,
        test_window_bars=args.test_window_bars,
        transaction_cost_bps=args.transaction_cost_bps,
        slippage_bps=args.slippage_bps,
    )
    write_benchmark_report(
        results,
        json_path=args.json_output,
        markdown_path=args.markdown_output,
    )

    print(json.dumps(benchmark_payload(results), sort_keys=True))


if __name__ == "__main__":
    main()

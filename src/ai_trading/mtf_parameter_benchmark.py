from __future__ import annotations

import argparse
import json
from collections.abc import Iterable
from dataclasses import asdict, dataclass
from math import isfinite, prod, sqrt
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
from .research_history import frozen_preprospective_history

_MIN_ACTIVE_PREDICTIONS = 20
_MIN_ACTIVE_PRECISION = 0.50
_MIN_ECONOMIC_TRADES = 20
_DEFAULT_TRANSACTION_COST_BPS = 2.0
_DEFAULT_SLIPPAGE_BPS = 1.0
_SIZED_STARTING_CASH = 100_000.0
_SIZED_POSITION_FRACTION = 0.10


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
        if not isfinite(self.minimum_threshold) or self.minimum_threshold < 0:
            raise ValueError("minimum_threshold must be finite and non-negative")
        if not isfinite(self.atr_multiplier) or self.atr_multiplier < 0:
            raise ValueError("atr_multiplier must be finite and non-negative")
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
class MTFResearchTrade:
    """Chronologically realized, non-overlapping research signal execution."""

    entry_time: str
    exit_time: str
    entry_price: float
    exit_price: float
    side: int


@dataclass(frozen=True)
class EconomicTradeQuality:
    """Descriptive after-cost outcomes. Not a promotion or execution gate.

    Wilson limits assume independent decisive trades; serial dependence can
    substantially widen actual uncertainty, even with disjoint executions.
    """

    winning_trades: int
    losing_trades: int
    flat_trades: int
    win_rate_all_trades: float | None
    decisive_win_rate: float | None
    decisive_win_rate_lower95: float | None
    decisive_win_rate_upper95: float | None
    mean_win_net_return: float | None
    mean_loss_abs_net_return: float | None
    payoff_ratio: float | None
    break_even_decisive_win_rate: float | None
    net_profit_factor: float | None


def summarize_economic_trade_quality(
    net_returns: Iterable[float],
) -> EconomicTradeQuality:
    """Describe net winning frequency AND gain/loss asymmetry, without tuning."""
    returns = tuple(float(value) for value in net_returns)
    if any(not isfinite(value) for value in returns):
        raise ValueError("economic trade returns must be finite")
    wins = [value for value in returns if value > 0.0]
    losses = [-value for value in returns if value < 0.0]
    total = len(returns)
    decisive = len(wins) + len(losses)
    avg_win = fmean(wins) if wins else None
    avg_loss = fmean(losses) if losses else None
    lower: float | None = None
    upper: float | None = None
    decisive_rate: float | None = None
    if decisive:
        decisive_rate = len(wins) / decisive
        # Descriptive Wilson 95% interval, NOT a valid test of dependent
        # market-trade edge or a license to change frozen parameters.
        z = 1.96
        denominator = 1.0 + z * z / decisive
        center = (decisive_rate + z * z / (2.0 * decisive)) / denominator
        half_width = (
            z * sqrt(
                decisive_rate * (1.0 - decisive_rate) / decisive
                + z * z / (4.0 * decisive * decisive)
            ) / denominator
        )
        lower = max(0.0, center - half_width)
        upper = min(1.0, center + half_width)
    return EconomicTradeQuality(
        winning_trades=len(wins),
        losing_trades=len(losses),
        flat_trades=total - decisive,
        win_rate_all_trades=len(wins) / total if total else None,
        decisive_win_rate=decisive_rate,
        decisive_win_rate_lower95=lower,
        decisive_win_rate_upper95=upper,
        mean_win_net_return=avg_win,
        mean_loss_abs_net_return=avg_loss,
        payoff_ratio=avg_win / avg_loss if avg_win is not None and avg_loss is not None else None,
        break_even_decisive_win_rate=(
            avg_loss / (avg_win + avg_loss)
            if avg_win is not None and avg_loss is not None else None
        ),
        net_profit_factor=sum(wins) / sum(losses) if losses else None,
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
    # Single-market, trade-close/held-bar mark-to-market research account.
    # No concurrent multi-asset portfolio, leverage or live execution.
    sized_equity_final: float = _SIZED_STARTING_CASH
    sized_net_return: float = 0.0
    sized_max_drawdown: float = 0.0
    paper_trades: tuple[MTFResearchTrade, ...] = ()
    economic_trade_quality: EconomicTradeQuality | None = None


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



def economic_cost_stress_report(result: MarketBenchmarkResult) -> dict[str, object]:
    """Replay the SAME retrospective trades under higher *assumed* costs.

    Cost sensitivity is diagnostic only; it must not select a configuration,
    refit a model or alter the frozen prospective registration. Holding fills
    and sides fixed also means this cannot model price impact or a broker.
    """
    if len(result.paper_trades) != result.economic_trades:
        raise ValueError("economic stress needs complete research trade evidence")
    if (
        not isfinite(result.transaction_cost_bps)
        or not isfinite(result.slippage_bps)
        or min(result.transaction_cost_bps, result.slippage_bps) < 0.0
    ):
        raise ValueError("economic stress costs must be finite and nonnegative")
    for trade in result.paper_trades:
        if (
            trade.side not in (-1, 1)
            or not isfinite(trade.entry_price)
            or not isfinite(trade.exit_price)
            or trade.entry_price <= 0.0
            or trade.exit_price <= 0.0
        ):
            raise ValueError("economic stress requires valid signed research fills")

    baseline_round_trip_bps = 2.0 * (
        result.transaction_cost_bps + result.slippage_bps
    )
    scenarios: dict[str, object] = {}
    for multiplier in (1, 2, 3):
        round_trip_fraction = baseline_round_trip_bps * multiplier / 10_000.0
        returns = tuple(
            trade.side * (trade.exit_price / trade.entry_price - 1.0)
            - round_trip_fraction
            for trade in result.paper_trades
        )
        if any(not isfinite(value) for value in returns):
            raise ValueError("economic cost stress resulted in a non-finite return")
        compounded = prod(max(0.0, 1.0 + ret) for ret in returns) - 1.0
        if not isfinite(compounded):
            raise ValueError("economic cost stress compounded return must be finite")
        diagnostics = summarize_economic_trade_quality(returns)
        scenarios[f"{multiplier}x"] = {
            "assumed_round_trip_cost_bps": baseline_round_trip_bps * multiplier,
            "trades": len(returns),
            "mean_net_return": fmean(returns) if returns else None,
            "compounded_net_return": float(compounded) if returns else None,
            "net_win_rate": diagnostics.win_rate_all_trades,
            "net_profit_factor": diagnostics.net_profit_factor,
        }

    # Guard against reporting a cost sensitivity series from unrelated fills.
    if result.paper_trades and abs(
        float(scenarios["1x"]["compounded_net_return"])
        - result.economic_compounded_net_return
    ) > 1e-9:
        raise ValueError("economic stress baseline does not reconcile")
    return {
        "scope": "retrospective_same_fills_hypothetical_no_promotion",
        "live_execution_validated": False,
        "stress_is_not_a_selection_gate": True,
        "scenarios": scenarios,
    }


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
            "sized_net_return": row.sized_net_return,
            "sized_max_drawdown": row.sized_max_drawdown,
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


def _mark_sized_paper_trade(
    market: pd.DataFrame,
    *,
    signal_pos: int,
    horizon_bars: int,
    side: int,
    equity: float,
    peak: float,
    max_drawdown: float,
    one_way_cost_bps: float,
) -> tuple[float, float, float]:
    """Mark a fixed-10%-notional, one-at-a-time research position on each close.

    Entry and exit are the *same* bars used by the independent-trade audit.
    Cash not allocated to the trade stays idle. This is not a multi-asset
    portfolio, funding/carry model or real fill simulation.
    """
    if side not in (-1, 1) or equity <= 0.0:
        raise ValueError("invalid signed position or research account equity")
    entry_pos = signal_pos + 1
    exit_pos = signal_pos + horizon_bars
    if exit_pos >= len(market):
        raise ValueError("trade exit extends past available completed bars")
    entry = float(market["Open"].iloc[entry_pos])
    if not isfinite(entry) or entry <= 0.0:
        raise ValueError("invalid next-open price for sized research account")
    cost_rate = one_way_cost_bps / 10_000.0
    units = equity * _SIZED_POSITION_FRACTION / entry
    entry_fee = units * entry * cost_rate
    marked = equity - entry_fee
    peak = max(peak, marked)
    max_drawdown = max(max_drawdown, 1.0 - marked / peak)
    for bar_pos in range(entry_pos, exit_pos + 1):
        close = float(market["Close"].iloc[bar_pos])
        if not isfinite(close) or close <= 0.0:
            raise ValueError("invalid close price for sized research account")
        marked = equity - entry_fee + side * units * (close - entry)
        if bar_pos == exit_pos:
            marked -= units * close * cost_rate
        if not isfinite(marked) or marked <= 0.0:
            raise ValueError("research equity exhausted; margin not modeled")
        peak = max(peak, marked)
        max_drawdown = max(max_drawdown, 1.0 - marked / peak)
    return marked, peak, max_drawdown


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
    test_start: pd.Timestamp | None = None,
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
    if test_start is None:
        windows = _fold_test_windows(
            usable,
            folds=folds,
            test_window_bars=test_window_bars,
            min_train_rows=min_train_rows,
        )
    else:
        # In a final holdout, every evaluated signal must occur at or after
        # the frozen split. Do not take the "last N" observations: gaps and
        # differing label horizons would silently shift the split per config.
        if folds != 1 or not isinstance(test_start, pd.Timestamp):
            raise ValueError("anchored holdout requires one fold and a timestamp")
        holdout_index = usable[usable >= test_start]
        if len(holdout_index) < 5:
            raise ValueError("holdout has insufficient matured evaluation bars")
        windows = (holdout_index,)

    market_positions = {timestamp: pos for pos, timestamp in enumerate(market.index)}
    predicted_sides: list[int] = []
    confidences: list[float] = []
    realized_labels: list[int] = []
    economic_returns: list[float] = []
    paper_trades: list[MTFResearchTrade] = []
    last_economic_exit_pos = -1
    sized_equity = _SIZED_STARTING_CASH
    sized_peak = _SIZED_STARTING_CASH
    sized_max_drawdown = 0.0
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
                paper_trades.append(
                    MTFResearchTrade(
                        entry_time=market.index[signal_pos + 1].isoformat(),
                        exit_time=market.index[signal_pos + config.horizon_bars].isoformat(),
                        entry_price=entry_open,
                        exit_price=exit_close,
                        side=effective_side,
                    )
                )
                sized_equity, sized_peak, sized_max_drawdown = _mark_sized_paper_trade(
                    market,
                    signal_pos=signal_pos,
                    horizon_bars=config.horizon_bars,
                    side=effective_side,
                    equity=sized_equity,
                    peak=sized_peak,
                    max_drawdown=sized_max_drawdown,
                    one_way_cost_bps=transaction_cost_bps + slippage_bps,
                )
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
    economic_trade_quality = summarize_economic_trade_quality(economic_returns)
    # A loss exceeding available capital is conservatively treated as ruin.
    economic_growth = prod(max(0.0, 1.0 + ret) for ret in economic_returns)
    if not isfinite(economic_growth):
        raise ValueError("non-finite compounded economic return")
    economic_net = float(economic_growth - 1.0)
    sized_net = sized_equity / _SIZED_STARTING_CASH - 1.0
    economic_gate_passed = (
        len(economic_returns) >= _MIN_ECONOMIC_TRADES
        and economic_mean > 0.0
        and economic_net > 0.0
        and sized_net > 0.0
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
        sized_equity_final=sized_equity,
        sized_net_return=float(sized_net),
        sized_max_drawdown=float(sized_max_drawdown),
        paper_trades=tuple(paper_trades),
        economic_trade_quality=economic_trade_quality,
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
    # An explicitly empty search is an error, never a request to execute the
    # potentially expensive default grid.
    grid = tuple(default_benchmark_grid() if configs is None else configs)
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


def run_chronological_holdout(
    markets: dict[str, pd.DataFrame],
    configs: Iterable[MTFBenchmarkConfig],
    *,
    holdout_bars: int = 480,
    validation_folds: int = 2,
    validation_test_window_bars: int = 240,
    min_train_rows: int = 500,
    random_state: int = 42,
    transaction_cost_bps: float = _DEFAULT_TRANSACTION_COST_BPS,
    slippage_bps: float = _DEFAULT_SLIPPAGE_BPS,
) -> dict[str, object]:
    """Freeze config selection before reading the final chronological slice.

    The final slice is held out from *this run's* parameter selection. It is
    not necessarily previously unseen across earlier research campaigns.
    A model is fitted on matured pre-holdout labels when evaluating the
    selected hyperparameters; no holdout outcomes inform the selection.
    """
    if not isinstance(holdout_bars, int) or holdout_bars < 5:
        raise ValueError("holdout_bars must be an integer >= 5")
    if not markets:
        raise ValueError("markets must not be empty")
    grid = tuple(configs)
    if not grid:
        raise ValueError("configs must not be empty")

    validation_markets: dict[str, pd.DataFrame] = {}
    cutoffs: dict[str, dict[str, str]] = {}
    for symbol, market in markets.items():
        if (
            not isinstance(market.index, pd.DatetimeIndex)
            or market.index.hasnans
            or market.index.has_duplicates
            or not market.index.is_monotonic_increasing
        ):
            raise ValueError(f"{symbol}: market timestamps must be valid and ordered")
        if len(market) <= holdout_bars:
            raise ValueError(f"{symbol}: not enough bars before holdout")
        validation_markets[symbol] = market.iloc[:-holdout_bars].copy()
        cutoffs[symbol] = {
            "validation_end": market.index[-holdout_bars - 1].isoformat(),
            "holdout_start": market.index[-holdout_bars].isoformat(),
            "holdout_end": market.index[-1].isoformat(),
        }

    validation_results = run_parameter_benchmark(
        validation_markets,
        configs=grid,
        folds=validation_folds,
        test_window_bars=validation_test_window_bars,
        min_train_rows=min_train_rows,
        random_state=random_state,
        transaction_cost_bps=transaction_cost_bps,
        slippage_bps=slippage_bps,
    )
    candidates = market_selections(validation_results)
    holdout: dict[str, dict[str, object]] = {}
    for symbol, selection in candidates.items():
        if selection is None:
            # Deliberately do not inspect later prices/returns after a
            # validation rejection; even a favorable holdout cannot rescue it.
            holdout[symbol] = {
                "status": "not_evaluated_no_validation_candidate",
                "passed": False,
                "result": None,
            }
            continue
        chosen = MTFBenchmarkConfig(**selection["config"])
        tested = evaluate_market_config(
            symbol,
            markets[symbol],
            chosen,
            folds=1,
            min_train_rows=min_train_rows,
            random_state=random_state,
            transaction_cost_bps=transaction_cost_bps,
            slippage_bps=slippage_bps,
            test_start=markets[symbol].index[-holdout_bars],
        )
        passed = bool(tested.directional_gate_passed and tested.economic_gate_passed)
        holdout[symbol] = {
            "status": "passed_for_manual_review" if passed else "failed",
            "passed": passed,
            "result": asdict(tested),
        }

    return {
        "method": {
            "selection": "validation_only",
            "holdout": "final_chronological_bars_excluded_from_selection",
            "holdout_bars_per_market": holdout_bars,
            "validation_folds": validation_folds,
            "validation_test_window_bars": validation_test_window_bars,
            "transaction_cost_bps_per_side": transaction_cost_bps,
            "slippage_bps_per_side": slippage_bps,
            "previously_unseen_across_research_runs": False,
            "full_portfolio_simulation": False,
            "paper_only": True,
            "auto_promote": False,
        },
        "cutoffs": cutoffs,
        "validation": benchmark_payload(validation_results),
        "holdout": holdout,
    }


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
                "win_rate_diagnostics": "descriptive_after_round_trip_costs_only",
                "wilson_interval": "95pct_decisive_trades_iid_assumption_not_a_live_gate",
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
                "sized_research_account": {
                    "starting_cash": _SIZED_STARTING_CASH,
                    "position_fraction": _SIZED_POSITION_FRACTION,
                    "marking": "each_completed_held_bar_close_and_exit_fees",
                    "accounting": "one_market_at_a_time_no_overlapping_positions",
                    "multi_market_aggregation": False,
                    "funding_borrow_margin_modeled": False,
                    "auto_promotion": False,
                },
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
                "markets": [
                    {**asdict(row), "economic_cost_stress": economic_cost_stress_report(row)}
                    for row in result.markets
                ],
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
        "two-sided modeled fees and slippage; a separate fixed-10%-notional",
        "single-market paper account marks each held close and reports drawdown.",
        "This is NOT multi-asset portfolio PnL, funding or broker execution.",
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
            "Active precision | Active n | Net return | Net n | "
            "Sized return | Sized DD | Cost gate | Brier | L/F/S |"
        )
        lines.append(
            "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | ---: | ---: |"
        )
        for row in result.markets:
            lines.append(
                f"| {row.symbol} | {row.selection_score:.4f} | "
                f"{row.macro_recall:.3f} | {row.directional_accuracy:.3f} | "
                f"{row.active_precision:.3f} | {row.active_predictions} | "
                f"{row.economic_compounded_net_return:+.2%} | "
                f"{row.economic_trades} | "
                f"{row.sized_net_return:+.2%} | "
                f"{row.sized_max_drawdown:.2%} | "
                f"{'PASS' if row.economic_gate_passed else 'FAIL'} | "
                f"{row.brier:.3f} | "
                f"{row.long_labels}/{row.flat_labels}/{row.short_labels} |"
            )
        lines.append("")
    lines.extend([
        "## After-cost win rate and break-even payoff diagnostics",
        "",
        "Observed win frequency is NOT net profitability. Net returns already",
        "include transaction costs and slippage on both entry and exit.",
        "Zero-net trades are not wins. Break-even hit rate and Wilson interval",
        "use decisive trades only; the Wilson calculation assumes independent",
        "trades, an approximation despite nonoverlapping research positions.",
        "No result here is a new prospective holdout or an automatic trade gate.",
        "",
        ("| Market | Frozen config | Win / loss / flat | Net win rate (all) | "
         "Decisive 95% Wilson interval | Break-even decisive win rate | "
         "Mean win / mean loss | Net profit factor |"),
        "| --- | --- | ---: | ---: | --- | ---: | --- | ---: |",
    ])
    for result in results:
        for row in result.markets:
            quality = row.economic_trade_quality
            if quality is None:
                lines.append(f"| {row.symbol} | {row.config_name} | N/A | N/A | N/A | N/A | N/A | N/A |")
                continue
            hit_rate = (
                f"{quality.win_rate_all_trades:.1%}"
                if quality.win_rate_all_trades is not None else "N/A"
            )
            interval = (
                f"{quality.decisive_win_rate_lower95:.1%}–"
                f"{quality.decisive_win_rate_upper95:.1%}"
                if quality.decisive_win_rate_lower95 is not None
                and quality.decisive_win_rate_upper95 is not None else "N/A"
            )
            break_even = (
                f"{quality.break_even_decisive_win_rate:.1%}"
                if quality.break_even_decisive_win_rate is not None else "N/A"
            )
            payoff = (
                f"{quality.mean_win_net_return:+.3%} / "
                f"{quality.mean_loss_abs_net_return:.3%}"
                if quality.mean_win_net_return is not None
                and quality.mean_loss_abs_net_return is not None else "N/A"
            )
            profit_factor = (
                f"{quality.net_profit_factor:.2f}"
                if quality.net_profit_factor is not None else "N/A"
            )
            lines.append(
                f"| {row.symbol} | {row.config_name} | "
                f"{quality.winning_trades}/{quality.losing_trades}/{quality.flat_trades} | "
                f"{hit_rate} | {interval} | {break_even} | {payoff} | {profit_factor} |"
            )
    lines.extend([
        "",
        "## Execution-cost stress, same research fills",
        "",
        "Replays precisely the original non-overlapping, next-open/horizon-close",
        "research trades with 1x, 2x and 3x assumed round-trip fees + slippage.",
        "Does not retune signals, simulate new executions, account for broker",
        "fills or establish prospective edge. Higher assumed costs may erase",
        "apparently favorable hit rates or compounded returns.",
        "",
        "| Market | Frozen config | Trades | 1x net | 2x net | 3x net | 2x profitable? |",
        "| --- | --- | ---: | ---: | ---: | ---: | --- |",
    ])
    for result in results:
        for row in result.markets:
            scenarios = economic_cost_stress_report(row)["scenarios"]
            formatted = []
            for key in ("1x", "2x", "3x"):
                value = scenarios[key]["compounded_net_return"]
                formatted.append(f"{value:+.2%}" if value is not None else "N/A")
            twice = scenarios["2x"]["compounded_net_return"]
            lines.append(
                f"| {row.symbol} | {row.config_name} | {row.economic_trades} | "
                f"{formatted[0]} | {formatted[1]} | {formatted[2]} | "
                f"{'yes' if twice is not None and twice > 0.0 else 'no'} |"
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

    # A rolling Yahoo "1mo" window includes new study bars after 2026-10-26.
    # Never let them enter retrospective tuning, fold selection or labels.
    markets = {
        symbol: frozen_preprospective_history(
            load_history(symbol, args.period, args.interval), symbol=symbol
        )
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

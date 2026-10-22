"""Read-only, chronological study of paper rebalance thresholds.

This is an offline walk-forward *proxy* model, not the hosted River-v1 model.
It must not automatically change paper configuration or enable live trading.
"""
from __future__ import annotations

from dataclasses import replace
from math import isfinite

import pandas as pd

from .backtest import WalkForwardBacktester, WalkForwardConfig
from .config import ModelConfig, RiskConfig

DEFAULT_THRESHOLDS = (0.0, 0.001, 0.0025, 0.005)
MIN_OOS_BARS = 240
MIN_OOS_TRADES = 30
MIN_FOLDS = 4
MIN_RETURN_ADVANTAGE = 0.0005
MAX_EXTRA_DRAWDOWN = 0.01


def _segment_performance(equity: pd.Series) -> tuple[float, float]:
    """Total return and peak-to-trough drawdown for a chronological segment."""
    if len(equity) < 2:
        raise ValueError("insufficient out-of-sample segment")
    values = equity.astype(float)
    if not all(isfinite(value) and value > 0 for value in values):
        raise ValueError("non-finite or non-positive backtest equity")
    net_return = float(values.iloc[-1] / values.iloc[0] - 1.0)
    drawdown = float((1.0 - values / values.cummax()).max())
    return net_return, drawdown


def compare_rebalance_thresholds(
    symbol: str,
    market: pd.DataFrame,
    *,
    risk_config: RiskConfig | None = None,
    model_config: ModelConfig | None = None,
    walk_forward_config: WalkForwardConfig | None = None,
    thresholds: tuple[float, ...] = DEFAULT_THRESHOLDS,
    holdout_fraction: float = 0.40,
) -> dict[str, object]:
    """Choose on early OOS validation, inspect untouched later OOS holdout.

    All strategies see the same chronological bars and cost model. The
    research model refits only on prior bars inside each purged WF fold.
    Comparing the holdout after selecting on validation avoids selecting
    thresholds based on a future period's returns.
    """
    if not symbol.strip():
        raise ValueError("symbol is required")
    if (
        not thresholds
        or thresholds[0] != 0.0
        or len(set(thresholds)) != len(thresholds)
        or any(not isfinite(t) or not 0.0 <= t <= 1.0 for t in thresholds)
    ):
        raise ValueError("thresholds must start with 0 and be distinct finite fractions")
    if not 0.2 <= holdout_fraction <= 0.5:
        raise ValueError("holdout_fraction must be in [0.2, 0.5]")

    risk = risk_config or RiskConfig()
    model = model_config or ModelConfig()
    config = walk_forward_config or WalkForwardConfig(
        min_train_bars=252,
        test_window_bars=240,
        max_train_bars=1000,
    )
    rows: list[dict[str, float | int]] = []
    reference_index: pd.Index | None = None
    split = 0
    for threshold in thresholds:
        scenario = replace(risk, min_rebalance_fraction=threshold)
        report = WalkForwardBacktester(
            risk_config=scenario,
            model_config=model,
            config=config,
        ).run(market)
        equity = report.equity_curve
        if reference_index is None:
            reference_index = equity.index
            if len(equity) < 4:
                raise ValueError("insufficient out-of-sample equity history")
            split = int((len(equity) - 1) * (1.0 - holdout_fraction))
        elif not reference_index.equals(equity.index):
            raise ValueError("threshold backtests produced misaligned OOS timestamps")

        validation_return, validation_dd = _segment_performance(
            equity.iloc[: split + 1]
        )
        holdout_return, holdout_dd = _segment_performance(equity.iloc[split:])
        full_return, full_dd = _segment_performance(equity)
        rows.append(
            {
                "threshold": threshold,
                "validation_net_return": validation_return,
                "validation_max_drawdown": validation_dd,
                "holdout_net_return": holdout_return,
                "holdout_max_drawdown": holdout_dd,
                "full_net_return": full_return,
                "full_max_drawdown": full_dd,
                "trades": int(report.trades),
                "folds": int(report.folds),
            }
        )

    assert reference_index is not None
    baseline = rows[0]
    enough_samples = (
        len(reference_index) >= MIN_OOS_BARS
        and baseline["trades"] >= MIN_OOS_TRADES
        and baseline["folds"] >= MIN_FOLDS
    )
    # Candidate choice uses ONLY validation returns, not holdout performance.
    candidates = [
        row
        for row in rows[1:]
        if (
            enough_samples
            and row["trades"] >= MIN_OOS_TRADES
            and row["folds"] >= MIN_FOLDS
            and row["validation_net_return"] > 0.0
            and row["validation_net_return"]
            >= baseline["validation_net_return"] + MIN_RETURN_ADVANTAGE
            and row["validation_max_drawdown"]
            <= baseline["validation_max_drawdown"] + MAX_EXTRA_DRAWDOWN
        )
    ]
    candidate = max(
        candidates,
        key=lambda row: (row["validation_net_return"], -row["threshold"]),
        default=None,
    )
    holdout_passed = bool(
        candidate is not None
        and candidate["holdout_net_return"] > 0.0
        and candidate["holdout_net_return"]
        >= baseline["holdout_net_return"] + MIN_RETURN_ADVANTAGE
        and candidate["holdout_max_drawdown"]
        <= baseline["holdout_max_drawdown"] + MAX_EXTRA_DRAWDOWN
    )

    return {
        "symbol": symbol,
        "model": "offline-walk-forward-proxy-not-river-v1",
        "interval_start": str(market.index[0]),
        "interval_end": str(market.index[-1]),
        "market_bars": len(market),
        "oos_bars": len(reference_index),
        "validation_end": str(reference_index[split]),
        "holdout_start": str(reference_index[split]),
        "holdout_end": str(reference_index[-1]),
        "transaction_cost_bps": risk.transaction_cost_bps,
        "slippage_bps": risk.slippage_bps,
        "minimum_oos_bars": MIN_OOS_BARS,
        "minimum_oos_trades": MIN_OOS_TRADES,
        "minimum_folds": MIN_FOLDS,
        "trials": rows,
        "sample_sufficient": enough_samples,
        "validation_selected_threshold": (
            candidate["threshold"] if candidate is not None else None
        ),
        "holdout_passed": holdout_passed,
        "review_only": True,
        "auto_enable": False,
        "note": (
            "Candidate chosen using earlier OOS returns only; holdout evaluated "
            "once afterwards. Offline model differs from hosted River-v1. "
            "Trade-count sufficiency is across all OOS periods, not holdout alone. "
            "No production parameter is changed."
        ),
    }

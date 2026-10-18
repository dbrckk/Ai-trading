"""Opt-in, offline Kronos challenger evaluation. Never routes or approves orders."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Protocol

import numpy as np
import pandas as pd


class ForecastPredictor(Protocol):
    def predict(self, **kwargs: object) -> pd.DataFrame: ...


@dataclass(frozen=True)
class ResearchConfig:
    lookback: int = 256
    horizon_bars: int = 9
    max_windows: int = 40
    threshold_bps: float = 5.0
    transaction_cost_bps: float = 2.0
    slippage_bps: float = 1.0
    sample_count: int = 3

    def __post_init__(self) -> None:
        if not 32 <= self.lookback <= 512:
            raise ValueError("lookback must be between 32 and 512")
        if not 1 <= self.horizon_bars <= min(120, self.lookback - 1):
            raise ValueError("horizon_bars must be between 1 and min(120, lookback - 1)")
        if not 1 <= self.max_windows <= 2000 or not 1 <= self.sample_count <= 20:
            raise ValueError("max_windows must be 1..2000 and sample_count must be 1..20")
        if any(
            not np.isfinite(value) or value < 0
            for value in (
                self.threshold_bps,
                self.transaction_cost_bps,
                self.slippage_bps,
            )
        ):
            raise ValueError("threshold and execution costs must be finite and non-negative")


def validate_market(frame: pd.DataFrame) -> pd.DataFrame:
    """Reject malformed time series rather than silently changing signal ordering."""
    if not isinstance(frame.index, pd.DatetimeIndex):
        raise ValueError("market index must contain timestamps")
    if frame.index.hasnans or frame.index.has_duplicates or not frame.index.is_monotonic_increasing:
        raise ValueError("market timestamps must be unique, valid and chronological")
    required = ("Open", "High", "Low", "Close")
    if not set(required).issubset(frame.columns):
        raise ValueError("market must contain Open/High/Low/Close")
    result = frame.copy()
    if "Volume" not in result.columns:
        result["Volume"] = 0.0
    columns = (*required, "Volume")
    result = result.loc[:, columns].apply(pd.to_numeric, errors="raise")
    if not np.isfinite(result.to_numpy(dtype=float)).all():
        raise ValueError("market contains non-finite OHLCV data")
    if bool((result.loc[:, required] <= 0).any().any()):
        raise ValueError("market contains non-positive prices")
    if bool((result["Volume"] < 0).any()):
        raise ValueError("market contains negative volume")
    if bool(
        (
            (result["High"] < result[["Open", "Close", "Low"]].max(axis=1))
            | (result["Low"] > result[["Open", "Close", "High"]].min(axis=1))
        ).any()
    ):
        raise ValueError("market contains inconsistent OHLC prices")
    return result


def _side(return_fraction: float, threshold_bps: float) -> int:
    if return_fraction > threshold_bps / 10_000:
        return 1
    if return_fraction < -threshold_bps / 10_000:
        return -1
    return 0


def _net_return(side: int, forward_return: float, config: ResearchConfig) -> float:
    if side == 0:
        return 0.0
    round_trip_cost = 2 * (config.transaction_cost_bps + config.slippage_bps) / 10_000
    return side * forward_return - round_trip_cost


def _bootstrap_lower(values: list[float], *, seed: int = 42) -> float | None:
    if len(values) < 30:
        return None
    generator = np.random.default_rng(seed)
    samples = np.asarray(values, dtype=float)
    means = np.mean(generator.choice(samples, size=(2000, len(samples))), axis=1)
    return float(np.quantile(means, 0.025))


def evaluate_walk_forward(
    market: pd.DataFrame,
    predictor: ForecastPredictor,
    config: ResearchConfig,
) -> dict[str, object]:
    """Evaluate non-overlapping realized windows; never send future OHLCV to Kronos."""
    market = validate_market(market)
    end_signal = len(market) - config.horizon_bars - 1
    if end_signal < config.lookback - 1:
        raise ValueError("not enough completed bars for lookback and future outcome")

    signal_positions = list(
        range(config.lookback - 1, end_signal + 1, config.horizon_bars)
    )[-config.max_windows :]
    observations: list[dict[str, object]] = []
    forecast_columns = {"Open": "open", "High": "high", "Low": "low", "Close": "close", "Volume": "volume"}

    for signal_pos in signal_positions:
        history = market.iloc[signal_pos + 1 - config.lookback : signal_pos + 1]
        future_times = market.index[signal_pos + 1 : signal_pos + config.horizon_bars + 1]
        forecast = predictor.predict(
            df=history.rename(columns=forecast_columns).reset_index(drop=True),
            x_timestamp=pd.Series(history.index),
            y_timestamp=pd.Series(future_times),
            pred_len=config.horizon_bars,
            T=1.0,
            top_p=0.9,
            sample_count=config.sample_count,
            verbose=False,
        )
        if len(forecast) != config.horizon_bars or "close" not in forecast:
            raise ValueError("Kronos returned an incomplete forecast")
        predicted_close = float(forecast["close"].iloc[-1])
        if not np.isfinite(predicted_close) or predicted_close <= 0:
            raise ValueError("Kronos returned an invalid forecast close")

        signal_close = float(history["Close"].iloc[-1])
        entry_open = float(market["Open"].iloc[signal_pos + 1])
        future_close = float(market["Close"].iloc[signal_pos + config.horizon_bars])
        predicted_return = predicted_close / signal_close - 1
        realized_return = future_close / entry_open - 1
        kronos_side = _side(predicted_return, config.threshold_bps)
        momentum_return = signal_close / float(history["Close"].iloc[-1 - config.horizon_bars]) - 1
        baseline_side = _side(momentum_return, config.threshold_bps)
        kronos_net = _net_return(kronos_side, realized_return, config)
        baseline_net = _net_return(baseline_side, realized_return, config)
        observations.append(
            {
                "signal_time": market.index[signal_pos].isoformat(),
                "outcome_time": future_times[-1].isoformat(),
                "predicted_return": predicted_return,
                "realized_return": realized_return,
                "kronos_side": kronos_side,
                "momentum_side": baseline_side,
                "kronos_net_return": kronos_net,
                "momentum_net_return": baseline_net,
            }
        )

    kronos = [float(item["kronos_net_return"]) for item in observations]
    baseline = [float(item["momentum_net_return"]) for item in observations]
    alpha = [k - b for k, b in zip(kronos, baseline, strict=True)]
    directional = [item for item in observations if item["kronos_side"] != 0]
    mean_lower = _bootstrap_lower(kronos)
    alpha_lower = _bootstrap_lower(alpha)
    summary = {
        "windows": len(observations),
        "directional_trades": len(directional),
        "hit_rate": (
            sum(item["kronos_side"] * item["realized_return"] > 0 for item in directional)
            / len(directional)
            if directional else None
        ),
        "mean_net_return": float(np.mean(kronos)),
        "momentum_mean_net_return": float(np.mean(baseline)),
        "mean_alpha_vs_momentum": float(np.mean(alpha)),
        "mean_net_return_ci95_lower": mean_lower,
        "mean_alpha_ci95_lower": alpha_lower,
        "review_eligible": (
            len(observations) >= 500
            and len(directional) >= 100
            and mean_lower is not None and mean_lower > 0
            and alpha_lower is not None and alpha_lower > 0
        ),
    }
    return {"config": asdict(config), "summary": summary, "observations": observations}


def load_predictor(source_dir: Path, model_size: str, device: str) -> ForecastPredictor:
    """Load the original upstream implementation, never a substitute predictor."""
    source_dir = source_dir.expanduser().resolve()
    if not (source_dir / "model" / "__init__.py").is_file():
        raise ValueError("--kronos-source must be a checkout of shiyu-coder/Kronos")
    if model_size not in {"mini", "small", "base"}:
        raise ValueError("model_size must be mini, small or base")
    sys.path.insert(0, str(source_dir))
    import torch  # noqa: PLC0415

    torch.manual_seed(42)
    from model import Kronos, KronosPredictor, KronosTokenizer  # type: ignore[import-not-found]  # noqa: PLC0415

    tokenizer_id = "NeoQuasar/Kronos-Tokenizer-2k" if model_size == "mini" else "NeoQuasar/Kronos-Tokenizer-base"
    tokenizer = KronosTokenizer.from_pretrained(tokenizer_id)
    model = Kronos.from_pretrained(f"NeoQuasar/Kronos-{model_size}")
    return KronosPredictor(
        model, tokenizer, max_context=2048 if model_size == "mini" else 512, device=device
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Offline Kronos paper-only quality research")
    parser.add_argument("--kronos-source", type=Path, required=True)
    parser.add_argument("--symbol", default="GC=F")
    parser.add_argument("--period", default="30d")
    parser.add_argument("--interval", default="5m")
    parser.add_argument("--csv", type=Path, help="Local OHLCV CSV with timestamp column")
    parser.add_argument("--model-size", choices=("mini", "small", "base"), default="mini")
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--lookback", type=int, default=256)
    parser.add_argument("--horizon-bars", type=int, default=9)
    parser.add_argument("--max-windows", type=int, default=40)
    parser.add_argument("--threshold-bps", type=float, default=5.0)
    parser.add_argument("--transaction-cost-bps", type=float, default=2.0)
    parser.add_argument("--slippage-bps", type=float, default=1.0)
    parser.add_argument("--sample-count", type=int, default=3)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    config = ResearchConfig(
        lookback=args.lookback,
        horizon_bars=args.horizon_bars,
        max_windows=args.max_windows,
        threshold_bps=args.threshold_bps,
        transaction_cost_bps=args.transaction_cost_bps,
        slippage_bps=args.slippage_bps,
        sample_count=args.sample_count,
    )
    if args.csv:
        frame = pd.read_csv(args.csv)
        if "timestamp" not in frame.columns:
            parser.error("CSV must include a timestamp column")
        frame["timestamp"] = pd.to_datetime(frame["timestamp"], utc=True, errors="raise")
        market = frame.set_index("timestamp")
    else:
        from .data import load_history  # noqa: PLC0415

        market = load_history(args.symbol, period=args.period, interval=args.interval)
    predictor = load_predictor(args.kronos_source, args.model_size, args.device)
    result = evaluate_walk_forward(market, predictor, config)
    result["provenance"] = {
        "symbol": args.symbol, "period": args.period, "interval": args.interval,
        "model": f"NeoQuasar/Kronos-{args.model_size}",
        "source": "https://github.com/shiyu-coder/Kronos",
        "paper_only": True, "seed": 42,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps(result["summary"], indent=2))


if __name__ == "__main__":
    main()

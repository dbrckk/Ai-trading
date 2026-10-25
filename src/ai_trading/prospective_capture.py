"""Prospective OHLCV acquisition only: no model training, signals or order placement."""

from __future__ import annotations

import argparse
import json
import os
from dataclasses import asdict
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from pathlib import Path

import pandas as pd

from .data import load_history
from .dataset_evidence import build_dataset_evidence

_OHLCV = ("Open", "High", "Low", "Close", "Volume")
_SYMBOL_FILES = {"GC=F": "gold", "^GDAXI": "dax", "BTC-USD": "btc"}
_INTERVAL = timedelta(minutes=5)
_CAPTURE_LAG = timedelta(minutes=15)
# Pin the exact registration bytes before the future acquisition boundary.
# The committed JSON cannot quietly drift while capturing new observations.
_REGISTERED_SHA256 = "7b8870cce74d7941ed6e3f3c33e0829cd28b2d92f32d11ab5ca8309daf48b096"


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        raise ValueError("prospective capture clock must be timezone-aware")
    return value.astimezone(UTC)


def prospective_snapshot(
    frame: pd.DataFrame,
    *,
    symbol: str,
    cutoff_utc: datetime,
    acquired_at_utc: datetime,
) -> dict[str, object]:
    """Record only 5m bars from the locked future boundary, once completed.

    Candles are indexed by their opening time; their close plus a 15-minute
    provider lag must be strictly before the acquisition timestamp. Never
    retroactively include earlier historical bars or rows with invalid prices.
    """
    cutoff = _as_utc(cutoff_utc)
    acquired = _as_utc(acquired_at_utc)
    if symbol not in _SYMBOL_FILES:
        raise ValueError("unsupported prospective market")
    if not isinstance(frame.index, pd.DatetimeIndex):
        raise TypeError("prospective bars require a datetime index")
    if frame.index.hasnans or frame.index.has_duplicates or not frame.index.is_monotonic_increasing:
        raise ValueError("prospective bar timestamps must be valid and ordered")
    if frame.index.tz is None:
        raise ValueError("prospective bars must have a timezone-aware index")
    if not set(_OHLCV).issubset(frame.columns):
        raise ValueError("prospective bars missing OHLCV")
    normalized = frame.loc[:, list(_OHLCV)].copy()
    normalized.index = normalized.index.tz_convert("UTC")
    numeric = normalized.apply(pd.to_numeric, errors="raise")
    # Reject invalid, nonpositive OHLC and negative/NaN volume rather than
    # making a retroactive repair of potentially tradable research data.
    if not (numeric.loc[:, list(_OHLCV[:4])] > 0).all().all():
        raise ValueError("prospective OHLC must be positive")
    if not (numeric["Volume"] >= 0).all():
        raise ValueError("prospective volume must be nonnegative")
    if not numeric.map(lambda value: pd.notna(value) and abs(value) != float("inf")).all().all():
        raise ValueError("prospective bars contain non-finite values")
    # All four prices must belong to the same physical candle range.
    # Check both boundaries explicitly; do not let an invalid high/low
    # silently pass into the immutable research evidence.
    if (
        (numeric["High"] < numeric["Low"]).any()
        or (numeric[["Open", "Close"]].gt(numeric["High"], axis=0)).any().any()
        or (numeric[["Open", "Close"]].lt(numeric["Low"], axis=0)).any().any()
    ):
        raise ValueError("prospective OHLC candle is inconsistent")
    # A provider can occasionally return a rounded or off-grid timestamp.
    # Such rows are not canonical opening times of registered 5m candles.
    if (
        (numeric.index.minute % 5 != 0).any()
        or (numeric.index.second != 0).any()
        or (numeric.index.microsecond != 0).any()
        or (numeric.index.nanosecond != 0).any()
    ):
        raise ValueError("prospective 5m opening timestamp is off-grid")

    latest_eligible_open = pd.Timestamp(acquired - _INTERVAL - _CAPTURE_LAG)
    selected = numeric.loc[
        (numeric.index >= pd.Timestamp(cutoff))
        & (numeric.index <= latest_eligible_open)
    ].copy()
    rows = [
        [timestamp.isoformat(), *[float(value) for value in row]]
        for timestamp, row in zip(
            selected.index, selected.to_numpy(), strict=True
        )
    ]
    evidence = (
        asdict(build_dataset_evidence(
            selected, provider="yahoo_yfinance_auto_adjusted",
            acquired_at_utc=acquired.isoformat(),
        ))
        if len(selected) else None
    )
    return {
        "schema_version": 1,
        "symbol": symbol,
        "status": "completed_bars_captured" if rows else "no_completed_bars",
        "observation_cutoff_utc": cutoff.isoformat(),
        "acquired_at_utc": acquired.isoformat(),
        "columns": list(_OHLCV),
        "timestamp_semantics": "opening_timestamp_utc",
        "completion_grace_minutes": 15,
        "bars": rows,
        "dataset_evidence": evidence,
        "training_or_strategy_selection_performed": False,
        "trading_enabled": False,
    }


def _dump(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, sort_keys=True, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )


def collect_prospective_bars(
    registration_file: Path,
    output_dir: Path,
    *,
    acquired_at_utc: datetime | None = None,
) -> dict[str, object]:
    """Archive future-only source bars and immutable per-run provenance."""
    registration_bytes = registration_file.read_bytes()
    if sha256(registration_bytes).hexdigest() != _REGISTERED_SHA256:
        raise ValueError("prospective registration hash mismatch")
    registration = json.loads(registration_bytes)
    if (
        registration.get("schema_version") != 1
        or registration.get("study_id") != "mtf-prospective-2026-10-26-v1"
        or registration.get("observation_start_utc")
        != "2026-10-26T00:00:00+00:00"
        or registration.get("bar_interval") != "5m"
        or registration.get("data_provider") != "yahoo_yfinance_auto_adjusted"
        or registration.get("minimum_completion_lag_minutes") != 15
        or registration.get("acquisition_window") != "5d"
        or registration.get("symbols") != list(_SYMBOL_FILES)
        or registration.get("frozen_research_comparators") != [
            {
                "horizon_bars": 9,
                "minimum_threshold": 0.0005,
                "atr_multiplier": 0.25,
                "max_train_rows": 1000,
                "min_confidence": 0.56,
            },
            {
                "horizon_bars": 9,
                "minimum_threshold": 0.0005,
                "atr_multiplier": 0.25,
                "max_train_rows": 1000,
                "min_confidence": 0.60,
            },
            {
                "horizon_bars": 18,
                "minimum_threshold": 0.0003,
                "atr_multiplier": 0.15,
                "max_train_rows": 1000,
                "min_confidence": 0.60,
            },
        ]
        or registration.get("hypothetical_costs_bps_per_side")
        != {"transaction": 2.0, "slippage": 1.0}
        or registration.get("live_broker_enabled") is not False
        or registration.get("permitted_actions")
        != ["archive_provider_ohlcv", "fingerprint_completed_bars", "report_missing_data"]
    ):
        raise ValueError("prospective registration was changed or is unsupported")
    cutoff = datetime.fromisoformat(registration["observation_start_utc"])
    acquired = _as_utc(acquired_at_utc or datetime.now(UTC))
    manifest: dict[str, object] = {
        "study_id": registration["study_id"],
        "registration_sha256": sha256(registration_bytes).hexdigest(),
        "registration_file": registration_file.as_posix(),
        "capture_commit": os.getenv("GITHUB_SHA", "local"),
        "capture_run_id": os.getenv("GITHUB_RUN_ID", "local"),
        "captured_at_utc": acquired.isoformat(),
        "observation_start_utc": cutoff.isoformat(),
        "market_status": {},
        "data_used_to_select_parameters": False,
        "promotions_or_trades_executed": False,
        "artifact_retention_is_finite": True,
    }
    statuses: dict[str, object] = {}
    for symbol, file_name in _SYMBOL_FILES.items():
        if acquired < cutoff + _INTERVAL + _CAPTURE_LAG:
            statuses[symbol] = "awaiting_future_completed_bars"
            continue
        try:
            frame = load_history(
                symbol, period="5d", interval="5m",
                max_attempts=2,
            )
            result = prospective_snapshot(
                frame, symbol=symbol, cutoff_utc=cutoff,
                acquired_at_utc=acquired,
            )
        except (ValueError, TypeError, OSError, RuntimeError):
            # Provider details can contain URLs or credentials; do not log.
            statuses[symbol] = "source_or_validation_failure"
            continue
        snapshot_path = output_dir / f"{file_name}.json"
        _dump(snapshot_path, result)
        evidence = result["dataset_evidence"]
        bars = result["bars"]
        latest_bar_utc = bars[-1][0] if bars else None
        has_same_day_bar = bool(
            latest_bar_utc is not None
            and _as_utc(datetime.fromisoformat(latest_bar_utc)).date()
            == acquired.date()
        )
        # A successful HTTP response may contain only earlier candles or
        # no completed future observations (e.g. on a closed market).
        # Keep an auditable empty snapshot, but never report acquisition as
        # successful without a nonempty, fingerprinted future-only dataset.
        statuses[symbol] = {
            "status": result["status"],
            "rows": len(bars),
            "dataset_sha256": evidence["data_hash"] if evidence else None,
            "file": snapshot_path.name,
            "file_sha256": sha256(snapshot_path.read_bytes()).hexdigest(),
            "latest_bar_utc": latest_bar_utc,
            "has_same_day_bar": has_same_day_bar,
        }
    manifest["market_status"] = statuses
    manifest["completed_market_count"] = sum(
        isinstance(item, dict)
        and item.get("status") == "completed_bars_captured"
        and isinstance(item.get("rows"), int)
        and not isinstance(item.get("rows"), bool)
        and item["rows"] > 0
        and isinstance(item.get("dataset_sha256"), str)
        and len(item["dataset_sha256"]) == 64
        for item in statuses.values()
    )
    # The 5-day provider window can contain only old sessions, so a valid
    # nonempty post-cutoff dataset does not prove a fresh daily acquisition.
    # On exchange holidays or stale feeds, archive what exists but fail
    # closed rather than reporting all markets newly collected.
    manifest["same_day_market_count"] = sum(
        isinstance(item, dict) and item.get("has_same_day_bar") is True
        for item in statuses.values()
    )
    manifest["all_markets_acquired"] = (
        manifest["completed_market_count"] == len(_SYMBOL_FILES)
        and manifest["same_day_market_count"] == len(_SYMBOL_FILES)
    )
    _dump(output_dir / "manifest.json", manifest)
    return manifest


def verify_capture_archive(output_dir: Path) -> None:
    """Independently recompute stored OHLCV evidence without provider access.

    A matching manifest file hash alone is insufficient: verify the frozen
    registration, temporal cutoff, candle validity and dataset hash against
    the *actual archived rows*. This performs no network or strategy work.
    """
    manifest = json.loads((output_dir / "manifest.json").read_text(encoding="utf-8"))
    if (
        manifest.get("study_id") != "mtf-prospective-2026-10-26-v1"
        or manifest.get("registration_sha256") != _REGISTERED_SHA256
        or manifest.get("observation_start_utc") != "2026-10-26T00:00:00+00:00"
    ):
        raise ValueError("prospective registration or study identity mismatch")
    cutoff = _as_utc(datetime.fromisoformat(manifest["observation_start_utc"]))
    acquired = _as_utc(datetime.fromisoformat(manifest["captured_at_utc"]))
    if manifest.get("promotions_or_trades_executed") is not False:
        raise ValueError("prospective archive must be observation only")
    if manifest.get("data_used_to_select_parameters") is not False:
        raise ValueError("prospective data must not be used to select parameters")
    statuses = manifest.get("market_status")
    if not isinstance(statuses, dict) or set(statuses) != set(_SYMBOL_FILES):
        raise ValueError("incomplete prospective market manifest")
    complete = 0
    same_day = 0
    for symbol, prefix in _SYMBOL_FILES.items():
        status = statuses[symbol]
        if status in ("awaiting_future_completed_bars", "source_or_validation_failure"):
            continue
        if not isinstance(status, dict) or status.get("file") != f"{prefix}.json":
            raise ValueError("invalid prospective market status")
        path = output_dir / f"{prefix}.json"
        raw = path.read_bytes()
        if sha256(raw).hexdigest() != status.get("file_sha256"):
            raise ValueError("prospective archive file hash mismatch")
        payload = json.loads(raw)
        bars = payload.get("bars")
        if (
            payload.get("symbol") != symbol
            or payload.get("acquired_at_utc") != acquired.isoformat()
            or not isinstance(bars, list)
        ):
            raise ValueError("invalid prospective archive payload")
        if not all(
            isinstance(bar, list)
            and len(bar) == len(_OHLCV) + 1
            and isinstance(bar[0], str)
            for bar in bars
        ):
            raise ValueError("invalid prospective OHLCV row shape")
        if len(bars) != status.get("rows"):
            raise ValueError("prospective archive row count mismatch")
        latest_bar_utc = bars[-1][0] if bars else None
        has_same_day_bar = bool(
            latest_bar_utc is not None
            and _as_utc(datetime.fromisoformat(latest_bar_utc)).date()
            == acquired.date()
        )
        if (
            status.get("latest_bar_utc") != latest_bar_utc
            or status.get("has_same_day_bar") is not has_same_day_bar
        ):
            raise ValueError("prospective market freshness evidence mismatch")
        if has_same_day_bar:
            same_day += 1

        index = pd.DatetimeIndex([datetime.fromisoformat(bar[0]) for bar in bars])
        if not bars:
            index = pd.DatetimeIndex([], tz="UTC")
        archived = pd.DataFrame(
            [bar[1:] for bar in bars], columns=list(_OHLCV), index=index
        )
        expected = prospective_snapshot(
            archived, symbol=symbol, cutoff_utc=cutoff, acquired_at_utc=acquired
        )
        # JSON round-trip handles the tuple/list difference in evidence columns.
        if json.dumps(payload, sort_keys=True, allow_nan=False) != json.dumps(
            expected, sort_keys=True, allow_nan=False
        ):
            raise ValueError("prospective independent OHLCV evidence mismatch")
        if bars:
            if (
                status.get("status") != "completed_bars_captured"
                or expected["dataset_evidence"]["data_hash"]
                != status.get("dataset_sha256")
            ):
                raise ValueError("prospective dataset evidence mismatch")
            complete += 1
        elif (
            status.get("status") != "no_completed_bars"
            or status.get("dataset_sha256") is not None
        ):
            raise ValueError("empty prospective archive status mismatch")
    if manifest.get("completed_market_count") != complete:
        raise ValueError("prospective completed market count mismatch")
    if manifest.get("same_day_market_count") != same_day:
        raise ValueError("prospective same-day market count mismatch")
    if manifest.get("all_markets_acquired") is not (
        complete == len(_SYMBOL_FILES) and same_day == len(_SYMBOL_FILES)
    ):
        raise ValueError("prospective acquisition flag mismatch")


def main() -> int:
    parser = argparse.ArgumentParser(description="Future-only MTF OHLCV archival")
    parser.add_argument(
        "--registration",
        default="research/mtf-prospective-2026-10-26-v1.json",
    )
    parser.add_argument(
        "--output-dir", default="artifacts/mtf-prospective"
    )
    parser.add_argument("--verify-only", action="store_true")
    args = parser.parse_args()
    if args.verify_only:
        try:
            verify_capture_archive(Path(args.output_dir))
        except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError):
            print("prospective archive integrity verification failed", flush=True)
            return 1
        print("Prospective archive integrity verified", flush=True)
        return 0
    try:
        result = collect_prospective_bars(
            Path(args.registration), Path(args.output_dir)
        )
    except (OSError, ValueError, TypeError, json.JSONDecodeError):
        print("prospective registration or local artifact invalid", flush=True)
        return 1
    print(
        "Prospective capture:"
        f" study={result['study_id']}"
        f" registration_sha256={result['registration_sha256']}"
        f" statuses={json.dumps(result['market_status'], sort_keys=True)}",
        flush=True,
    )
    if not result["all_markets_acquired"] and all(
        value == "awaiting_future_completed_bars"
        for value in result["market_status"].values()
    ):
        print("Registration frozen; capture not started before future cutoff", flush=True)
        return 0
    return 0 if result["all_markets_acquired"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

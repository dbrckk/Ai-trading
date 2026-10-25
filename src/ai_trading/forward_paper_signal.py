"""Timestamped read-only River-v1 paper signal observations, never order advice.

This observer is intentionally separate from the frozen MTF OHLCV collector.
It archives the signal exposed by the public paper dashboard only AFTER the
HTTP response, and defines a strictly future hypothetical entry boundary.
A River-v1 observation does not constitute a frozen MTF model prediction.
"""

from __future__ import annotations

import argparse
import json
import os
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from math import isfinite
from pathlib import Path
from urllib.request import Request, urlopen

_START_UTC = datetime(2026, 10, 26, tzinfo=UTC)
_BASE_URL = "https://ai-trading-dashboard-qyr2.onrender.com"
_MARKETS = ("GC=F", "^GDAXI", "BTC-USD")
_SIDES = {"LONG": 1, "FLAT": 0, "SHORT": -1}
_STATES = ("PAPER_APPROVED", "RISK_REJECTED", "NO_TRADE")
_MAX_BODY_BYTES = 1_000_000
_MAX_SIGNAL_AGE = timedelta(minutes=15)
_BAR_SECONDS = 300


def _utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        raise ValueError("observer clock must be timezone-aware")
    return value.astimezone(UTC)


def _next_future_open(after: datetime) -> datetime:
    second = int(_utc(after).timestamp())
    return datetime.fromtimestamp((second // _BAR_SECONDS + 1) * _BAR_SECONDS, tz=UTC)


def _read_dashboard_json(path: str) -> tuple[dict[str, object], str]:
    """Read bounded public JSON by GET only; never call scheduler endpoints."""
    if path not in {"/livez", "/api/markets"}:
        raise ValueError("observer may read only public health and market GETs")
    request = Request(
        _BASE_URL + path,
        headers={"Accept": "application/json", "User-Agent": "ai-trading-forward-audit/1"},
        method="GET",
    )
    with urlopen(request, timeout=15) as response:
        if response.status != 200:
            raise ValueError("dashboard observation HTTP failure")
        if "application/json" not in response.headers.get("Content-Type", ""):
            raise ValueError("dashboard observation content type invalid")
        raw = response.read(_MAX_BODY_BYTES + 1)
    if len(raw) > _MAX_BODY_BYTES:
        raise ValueError("dashboard observation exceeds permitted size")
    data = json.loads(raw)
    if not isinstance(data, dict):
        raise ValueError("dashboard observation JSON must be an object")
    return data, sha256(raw).hexdigest()


def build_forward_paper_observation(
    dashboard: dict[str, object],
    *,
    deployed_commit: str,
    observed_at_utc: datetime,
    market_response_sha256: str,
    liveness_response_sha256: str,
) -> dict[str, object]:
    """Read current paper decisions, not frozen MTF forecasts or fills.

    Signals are only eligible as *future* observational baselines if a new
    5-minute entry bar starts after the observation has been captured.
    """
    observed = _utc(observed_at_utc)
    if observed < _START_UTC:
        raise ValueError("forward observation cannot predate study start")
    markets = dashboard.get("markets")
    if not isinstance(markets, list) or len(markets) != len(_MARKETS):
        raise ValueError("observer requires exactly three market records")
    by_symbol = {}
    for item in markets:
        if not isinstance(item, dict) or item.get("symbol") not in _MARKETS:
            raise ValueError("invalid observed market")
        symbol = item["symbol"]
        if symbol in by_symbol:
            raise ValueError("duplicate observed market")
        by_symbol[symbol] = item
    if set(by_symbol) != set(_MARKETS):
        raise ValueError("missing observed paper market")
    if not isinstance(deployed_commit, str) or len(deployed_commit) != 40:
        raise ValueError("source deployed commit must be a complete SHA")
    for value in (market_response_sha256, liveness_response_sha256):
        if not isinstance(value, str) or len(value) != 64:
            raise ValueError("source body hash must be SHA-256")

    next_open = _next_future_open(observed)
    rows = []
    for symbol in _MARKETS:
        item = by_symbol[symbol]
        overview = item.get("overview")
        overview = overview if isinstance(overview, dict) else {}
        model = overview.get("model")
        model = model if isinstance(model, dict) else {}
        status = item.get("signal_state")
        side_label = item.get("signal")
        confidence = item.get("confidence")
        source_signal_time = item.get("signal_time")
        valid_source_time = False
        parsed_source_time: datetime | None = None
        if isinstance(source_signal_time, str):
            try:
                parsed_source_time = _utc(datetime.fromisoformat(source_signal_time))
                valid_source_time = (
                    timedelta(0) <= observed - parsed_source_time <= _MAX_SIGNAL_AGE
                )
            except ValueError:
                pass
        score_valid = (
            isinstance(confidence, (int, float))
            and not isinstance(confidence, bool)
            and isfinite(confidence)
            and 0.0 <= confidence <= 1.0
        )
        model_checksum = model.get("checksum")
        model_valid = (
            model.get("present") is True
            and model.get("format") == "joblib-river-v1"
            and model.get("version") == 1
            and isinstance(model_checksum, str)
            and len(model_checksum) >= 10
        )
        eligible = (
            item.get("freshness") == "LIVE"
            and item.get("session_open") is True
            and overview.get("engine_status") == "RUNNING"
            and status in _STATES
            and side_label in _SIDES
            and score_valid
            and model_valid
            and valid_source_time
            and isinstance(item.get("risk_approved"), bool)
            and (
                (status == "PAPER_APPROVED" and item["risk_approved"])
                or (status == "RISK_REJECTED" and not item["risk_approved"])
                or (status == "NO_TRADE" and side_label == "FLAT")
            )
        )
        rows.append({
            "symbol": symbol,
            "source_signal_time_utc": (
                parsed_source_time.isoformat() if parsed_source_time is not None else None
            ),
            "source_signal_state": status if isinstance(status, str) else None,
            "source_freshness": item.get("freshness"),
            "source_engine_status": overview.get("engine_status"),
            "observed_model_family": "river-v1",
            "model_checksum_prefix": model_checksum if model_valid else None,
            "model_checksum_is_truncated": True,
            "signal": side_label if eligible else None,
            "confidence": float(confidence) if eligible else None,
            "risk_approved": item.get("risk_approved") if eligible else None,
            "future_observation_eligible": bool(eligible),
            "earliest_hypothetical_entry_open_utc": next_open.isoformat(),
            "execution_status": "no_order_placed",
        })
    return {
        "schema_version": 1,
        "capture_type": "read_only_paper_river_v1_observation_not_frozen_mtf",
        "linked_study_start_utc": _START_UTC.isoformat(),
        "observed_at_utc": observed.isoformat(),
        "deployed_commit": deployed_commit,
        "market_response_sha256": market_response_sha256,
        "liveness_response_sha256": liveness_response_sha256,
        "capture_commit": os.getenv("GITHUB_SHA", "local"),
        "capture_run_id": os.getenv("GITHUB_RUN_ID", "local"),
        "markets": rows,
        "eligible_markets": sum(row["future_observation_eligible"] for row in rows),
        "training_or_strategy_selection_performed": False,
        "orders_or_promotions_executed": False,
        "frozen_mtf_comparators_evaluated": False,
        "performance_claim_validated": False,
        "artifact_retention_is_finite": True,
    }


def _write_archive(target: Path, record: dict[str, object]) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(record, sort_keys=True, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )


def verify_forward_paper_archive(target: Path) -> None:
    """Offline structural/temporal validation; no model or API invocation."""
    payload = json.loads(target.read_text(encoding="utf-8"))
    if (
        payload.get("schema_version") != 1
        or payload.get("capture_type")
        != "read_only_paper_river_v1_observation_not_frozen_mtf"
        or payload.get("training_or_strategy_selection_performed") is not False
        or payload.get("orders_or_promotions_executed") is not False
        or payload.get("frozen_mtf_comparators_evaluated") is not False
        or payload.get("performance_claim_validated") is not False
        or payload.get("linked_study_start_utc") != _START_UTC.isoformat()
    ):
        raise ValueError("invalid forward paper research scope")
    timestamp = _utc(datetime.fromisoformat(payload["observed_at_utc"]))
    if timestamp < _START_UTC:
        if payload.get("status") != "awaiting_cutoff" or payload.get("markets") != []:
            raise ValueError("invalid pre-cutoff forward archive")
        return
    for field, length in (("deployed_commit", 40),
                          ("market_response_sha256", 64),
                          ("liveness_response_sha256", 64)):
        value = payload.get(field)
        if not isinstance(value, str) or len(value) != length:
            raise ValueError("invalid forward paper source fingerprint")
    markets = payload.get("markets")
    if not isinstance(markets, list) or len(markets) != len(_MARKETS):
        raise ValueError("missing forward paper market observation")
    if tuple(row.get("symbol") for row in markets) != _MARKETS:
        raise ValueError("forward paper markets are incomplete or misordered")
    expected_entry = _next_future_open(timestamp).isoformat()
    eligible = 0
    for item in markets:
        if item.get("earliest_hypothetical_entry_open_utc") != expected_entry:
            raise ValueError("forward paper entry timestamp is not strictly future")
        if item.get("observed_model_family") != "river-v1":
            raise ValueError("wrong paper model family")
        if item.get("execution_status") != "no_order_placed":
            raise ValueError("unexpected forward paper execution")
        if item.get("future_observation_eligible") is True:
            if (
                item.get("source_freshness") != "LIVE"
                or item.get("source_engine_status") != "RUNNING"
                or item.get("source_signal_state") not in _STATES
                or not isinstance(item.get("model_checksum_prefix"), str)
                or len(item["model_checksum_prefix"]) < 10
                or item.get("model_checksum_is_truncated") is not True
                or not isinstance(item.get("risk_approved"), bool)
            ):
                raise ValueError("unverified forward paper source status")
            state = item["source_signal_state"]
            if not (
                (state == "PAPER_APPROVED" and item["risk_approved"]
                 and item.get("signal") != "FLAT")
                or (state == "RISK_REJECTED" and not item["risk_approved"])
                or (state == "NO_TRADE" and item.get("signal") == "FLAT")
            ):
                raise ValueError("forward paper risk state mismatch")
            if (
                item.get("signal") not in _SIDES
                or not isinstance(item.get("confidence"), (int, float))
                or isinstance(item.get("confidence"), bool)
                or not isfinite(item["confidence"])
                or not 0.0 <= item["confidence"] <= 1.0
            ):
                raise ValueError("invalid forward paper signal")
            signal_time = _utc(datetime.fromisoformat(item["source_signal_time_utc"]))
            if not timedelta(0) <= timestamp - signal_time <= _MAX_SIGNAL_AGE:
                raise ValueError("paper observation signal is not fresh")
            eligible += 1
        elif item.get("future_observation_eligible") is not False:
            raise ValueError("invalid forward paper eligibility flag")
        elif item.get("signal") is not None or item.get("confidence") is not None:
            raise ValueError("ineligible market must not carry a tradable signal")
    if payload.get("eligible_markets") != eligible:
        raise ValueError("forward paper eligible count mismatch")


def main() -> int:
    parser = argparse.ArgumentParser(description="Read-only future paper signal logger")
    parser.add_argument("--output-dir", default="artifacts/forward-paper-signals")
    parser.add_argument("--verify-only", action="store_true")
    args = parser.parse_args()
    path = Path(args.output_dir) / "observation.json"
    if args.verify_only:
        try:
            verify_forward_paper_archive(path)
        except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError):
            print("forward paper archive invalid", flush=True)
            return 1
        print("forward paper archive verified", flush=True)
        return 0
    started = datetime.now(UTC)
    if started < _START_UTC:
        _write_archive(path, {
            "schema_version": 1,
            "capture_type": "read_only_paper_river_v1_observation_not_frozen_mtf",
            "status": "awaiting_cutoff",
            "linked_study_start_utc": _START_UTC.isoformat(),
            "observed_at_utc": started.isoformat(),
            "markets": [],
            "training_or_strategy_selection_performed": False,
            "orders_or_promotions_executed": False,
            "frozen_mtf_comparators_evaluated": False,
            "performance_claim_validated": False,
        })
        print("paper forecast evidence frozen until prospective start", flush=True)
        return 0
    try:
        liveness, live_hash = _read_dashboard_json("/livez")
        markets, market_hash = _read_dashboard_json("/api/markets")
        record = build_forward_paper_observation(
            markets,
            deployed_commit=liveness["deployed_commit"],
            observed_at_utc=datetime.now(UTC),
            market_response_sha256=market_hash,
            liveness_response_sha256=live_hash,
        )
        _write_archive(path, record)
        verify_forward_paper_archive(path)
    except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError):
        print("forward paper source unavailable or invalid; no fabricated record", flush=True)
        return 1
    print(
        "Paper forward observer: "
        f"markets={len(record['markets'])} eligible={record['eligible_markets']} "
        "(River-v1 research only, never frozen MTF evidence)",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import datetime
from math import isclose, isfinite

from .market_freshness import classify_market_freshness
from .operational_overview import build_operational_overview
from .paper_cycle import PaperCycleResult
from .paper_cycle_service import (
    PaperCycleServiceError,
    ProductionPaperCycleSettings,
    run_production_paper_cycle,
)
from .performance_metrics import empty_performance_payload, performance_payload
from .persistence import PaperPersistence, build_runtime_key
from .persistence_factory import build_paper_persistence
from .runtime_status import runtime_status_snapshot

_NORMALIZED_RUNTIME_CASH = 100_000.0


@dataclass(frozen=True)
class MarketSpec:
    symbol: str
    label: str
    allocation: float

    def __post_init__(self) -> None:
        if not self.symbol.strip():
            raise ValueError("market symbol must not be empty")
        if not self.label.strip():
            raise ValueError("market label must not be empty")
        if not isfinite(self.allocation) or not 0.0 < self.allocation <= 1.0:
            raise ValueError("market allocation must be finite and in (0, 1]")


def _validate_market_bundle(markets: tuple[MarketSpec, ...]) -> None:
    if not markets:
        raise ValueError("markets must not be empty")
    symbols = tuple(market.symbol for market in markets)
    if len(set(symbols)) != len(symbols):
        raise ValueError("market symbols must be unique")
    total_allocation = sum(market.allocation for market in markets)
    if not isclose(total_allocation, 1.0, rel_tol=0.0, abs_tol=1e-9):
        raise ValueError("market allocations must sum to 1.0")


DEFAULT_MARKETS: tuple[MarketSpec, ...] = (
    MarketSpec("GC=F", "Gold", 0.34),
    MarketSpec("^GDAXI", "DAX", 0.33),
    MarketSpec("BTC-USD", "BTC / USD", 0.33),
)


def configured_markets_from_env() -> tuple[MarketSpec, ...]:
    raw = os.getenv("AI_TRADING_MARKETS", "").strip()
    if not raw:
        return DEFAULT_MARKETS

    symbols = tuple(part.strip() for part in raw.split(",") if part.strip())
    if not symbols:
        raise ValueError("AI_TRADING_MARKETS must contain at least one symbol")

    known = {spec.symbol: spec for spec in DEFAULT_MARKETS}
    if symbols == tuple(spec.symbol for spec in DEFAULT_MARKETS):
        return DEFAULT_MARKETS

    weight = 1.0 / len(symbols)
    return tuple(
        MarketSpec(
            symbol=symbol,
            label=known.get(symbol, MarketSpec(symbol, symbol, weight)).label,
            allocation=weight,
        )
        for symbol in symbols
    )


def run_multi_market_paper_cycle(
    markets: tuple[MarketSpec, ...],
    *,
    period: str,
    interval: str,
    max_catchup_bars: int,
    poll_seconds: float,
    shadow_challenger_enabled: bool,
    mtf_period: str = "1mo",
    persistence: PaperPersistence | None = None,
) -> PaperCycleResult:
    _validate_market_bundle(markets)

    backend = persistence
    if backend is None:
        try:
            backend = build_paper_persistence()
        except Exception as exc:  # noqa: BLE001 - sanitize provider failures
            raise PaperCycleServiceError(
                code="storage_unavailable",
                error_type=type(exc).__name__,
            ) from None

    processed = 0
    remaining_backlog = False
    processed_bars = 0
    last_processed: str | None = None
    mtf_evaluated = False
    failures: list[tuple[str, str]] = []

    def run_market(market: MarketSpec):
        return run_production_paper_cycle(
            ProductionPaperCycleSettings(
                symbol=market.symbol,
                period=period,
                interval=interval,
                max_catchup_bars=max_catchup_bars,
                poll_seconds=poll_seconds,
                shadow_challenger_enabled=shadow_challenger_enabled,
                mtf_period=mtf_period,
            ),
            persistence=backend,
        )

    with ThreadPoolExecutor(max_workers=min(4, len(markets))) as executor:
        futures = {
            executor.submit(run_market, market): market
            for market in markets
        }
        for future in as_completed(futures):
            market = futures[future]
            try:
                result = future.result()
            except PaperCycleServiceError as exc:
                failures.append((market.symbol, exc.code))
                continue

            processed += result.processed
            processed_bars += result.processed_bars
            remaining_backlog = remaining_backlog or result.remaining_backlog
            mtf_evaluated = mtf_evaluated or result.mtf_evaluated
            if result.last_processed is not None:
                last_processed = (
                    result.last_processed
                    if last_processed is None
                    else max(last_processed, result.last_processed)
                )

    if len(failures) == len(markets):
        failure_codes = {code for _, code in failures}
        code = (
            "storage_unavailable"
            if "storage_unavailable" in failure_codes
            else "execution_failed"
        )
        raise PaperCycleServiceError(
            code=code,
            error_type="MultiMarketFailure",
        )

    reason = f"processed {processed} bar(s) across {len(markets) - len(failures)} market(s)"
    if failures:
        reason += f"; isolated failures={len(failures)}"

    return PaperCycleResult(
        processed=processed,
        remaining_backlog=remaining_backlog,
        last_processed=last_processed,
        processed_bars=processed_bars,
        reason=reason,
        mtf_evaluated=mtf_evaluated,
    )


def build_multi_market_overview(
    persistence: PaperPersistence,
    markets: tuple[MarketSpec, ...],
    *,
    interval: str,
    portfolio_cash: float = 100_000.0,
    now: datetime | None = None,
) -> dict[str, object]:
    _validate_market_bundle(markets)

    market_rows: list[dict[str, object]] = []
    portfolio_equity = 0.0
    healthy_markets = 0
    running_markets = 0
    stale_markets = 0
    error_markets = 0
    alert_markets = 0
    closed_markets = 0
    catching_up_markets = 0
    provider_gap_markets = 0
    runtime_keys = tuple(
        build_runtime_key(market.symbol, interval)
        for market in markets
    )
    portfolio_performance = empty_performance_payload()
    load_portfolio_performance = getattr(
        persistence,
        "load_portfolio_trade_performance",
        None,
    )
    if callable(load_portfolio_performance):
        try:
            portfolio_performance = performance_payload(
                load_portfolio_performance(runtime_keys)
            )
        except Exception:  # noqa: BLE001 - optional observer must not break overview
            portfolio_performance = empty_performance_payload()

    for market in markets:
        runtime_key = build_runtime_key(market.symbol, interval)
        allocated_cash = portfolio_cash * market.allocation
        try:
            persisted = persistence.load_runtime(runtime_key, _NORMALIZED_RUNTIME_CASH)
            normalized_equity = (
                persisted.state.cash
                + persisted.state.units * persisted.state.last_price
            )
            sleeve_equity = allocated_cash * normalized_equity / _NORMALIZED_RUNTIME_CASH
            overview = build_operational_overview(
                persistence,
                runtime_key,
                _NORMALIZED_RUNTIME_CASH,
            )
            status = persistence.load_runtime_status(runtime_key)
            market_signal = None
            market_confidence = None
            market_reason = None
            cycle_duration_seconds = None
            market_mtf_evaluated = False
            heartbeat_age_seconds = None
            freshness = "OFF"
            if status is not None:
                market_signal = (
                    {1: "LONG", -1: "SHORT", 0: "FLAT"}.get(status.side)
                    if status.processed
                    else None
                )
                market_confidence = status.confidence if status.processed else None
                market_reason = status.reason
                cycle_duration_seconds = status.cycle_duration_seconds
                market_mtf_evaluated = status.mtf_evaluated
                status_snapshot = runtime_status_snapshot(status, now=now)
                heartbeat_age_seconds = status_snapshot.get("heartbeat_age_seconds")
                freshness, session_open = classify_market_freshness(
                    market.symbol,
                    status,
                    status_snapshot,
                    now=now,
                )
            else:
                session_open = None
            healthy = bool(overview.get("storage_healthy"))
            if healthy:
                healthy_markets += 1

            engine_status = str(overview.get("engine_status") or "UNKNOWN").upper()
            if engine_status == "RUNNING":
                running_markets += 1
            elif engine_status == "STALE":
                stale_markets += 1
            elif engine_status == "ERROR":
                error_markets += 1
            if overview.get("alerts"):
                alert_markets += 1
            if freshness == "MARKET_CLOSED":
                closed_markets += 1
            elif freshness == "CATCHING_UP":
                catching_up_markets += 1
            elif freshness == "PROVIDER_GAP":
                provider_gap_markets += 1

            portfolio_equity += sleeve_equity
            market_rows.append(
                {
                    "symbol": market.symbol,
                    "label": market.label,
                    "allocation": market.allocation,
                    "allocated_cash": allocated_cash,
                    "equity": sleeve_equity,
                    "pnl": sleeve_equity - allocated_cash,
                    "normalized_equity": normalized_equity,
                    "runtime_key": runtime_key,
                    "signal": market_signal,
                    "confidence": market_confidence,
                    "reason": market_reason,
                    "cycle_duration_seconds": cycle_duration_seconds,
                    "mtf_evaluated": market_mtf_evaluated,
                    "heartbeat_age_seconds": heartbeat_age_seconds,
                    "freshness": freshness,
                    "session_open": session_open,
                    "overview": overview,
                }
            )
        except Exception:  # noqa: BLE001 - isolate one market from the dashboard
            error_markets += 1
            alert_markets += 1
            market_rows.append(
                {
                    "symbol": market.symbol,
                    "label": market.label,
                    "allocation": market.allocation,
                    "allocated_cash": allocated_cash,
                    "equity": None,
                    "pnl": None,
                    "normalized_equity": None,
                    "runtime_key": runtime_key,
                    "heartbeat_age_seconds": None,
                    "freshness": "ERROR",
                    "session_open": None,
                    "overview": {
                        "storage_healthy": False,
                        "engine_status": "ERROR",
                        "processed_bars": None,
                        "last_processed": None,
                        "shadow_challenger": {
                            "status": "unavailable",
                            "observations": 0,
                        },
                        "alerts": ["market unavailable"],
                    },
                }
            )

    return {
        "portfolio": {
            "starting_cash": portfolio_cash,
            "equity": portfolio_equity,
            "pnl": portfolio_equity - portfolio_cash,
            "markets": len(markets),
            "healthy_markets": healthy_markets,
            "running_markets": running_markets,
            "stale_markets": stale_markets,
            "error_markets": error_markets,
            "alert_markets": alert_markets,
            "closed_markets": closed_markets,
            "catching_up_markets": catching_up_markets,
            "provider_gap_markets": provider_gap_markets,
            "performance": portfolio_performance,
        },
        "markets": market_rows,
    }

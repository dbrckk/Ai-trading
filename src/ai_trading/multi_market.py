from __future__ import annotations

import os
from dataclasses import dataclass

from .operational_overview import build_operational_overview
from .paper_cycle import PaperCycleResult
from .paper_cycle_service import (
    PaperCycleServiceError,
    ProductionPaperCycleSettings,
    run_production_paper_cycle,
)
from .persistence import PaperPersistence, build_runtime_key
from .persistence_factory import build_paper_persistence

_NORMALIZED_RUNTIME_CASH = 100_000.0


@dataclass(frozen=True)
class MarketSpec:
    symbol: str
    label: str
    allocation: float


DEFAULT_MARKETS: tuple[MarketSpec, ...] = (
    MarketSpec("GC=F", "Gold", 0.34),
    MarketSpec("^GDAXI", "DAX", 0.33),
    MarketSpec("BTC-USD", "BTC / USD", 0.33),
)


def configured_markets_from_env() -> tuple[MarketSpec, ...]:
    raw = os.getenv("AI_TRADING_MARKETS", "").strip()
    if not raw:
        return (MarketSpec("GC=F", "Gold", 1.0),)

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
    persistence: PaperPersistence | None = None,
) -> PaperCycleResult:
    if not markets:
        raise ValueError("markets must not be empty")

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
    failures: list[tuple[str, str]] = []

    for market in markets:
        try:
            result = run_production_paper_cycle(
                ProductionPaperCycleSettings(
                    symbol=market.symbol,
                    period=period,
                    interval=interval,
                    max_catchup_bars=max_catchup_bars,
                    poll_seconds=poll_seconds,
                    shadow_challenger_enabled=shadow_challenger_enabled,
                ),
                persistence=backend,
            )
        except PaperCycleServiceError as exc:
            failures.append((market.symbol, exc.code))
            continue

        processed += result.processed
        processed_bars += result.processed_bars
        remaining_backlog = remaining_backlog or result.remaining_backlog
        last_processed = result.last_processed or last_processed

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
    )


def build_multi_market_overview(
    persistence: PaperPersistence,
    markets: tuple[MarketSpec, ...],
    *,
    interval: str,
    portfolio_cash: float = 100_000.0,
) -> dict[str, object]:
    market_rows: list[dict[str, object]] = []
    portfolio_equity = 0.0
    healthy_markets = 0

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
            healthy = bool(overview.get("storage_healthy"))
            if healthy:
                healthy_markets += 1
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
                    "overview": overview,
                }
            )
        except Exception:  # noqa: BLE001 - isolate one market from the dashboard
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
        },
        "markets": market_rows,
    }

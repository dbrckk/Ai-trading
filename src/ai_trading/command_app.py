from __future__ import annotations

from datetime import UTC, datetime

import typer

from .cli import app, console
from .config import RiskConfig
from .paper_cycle import PaperCycleRunner
from .persistence import build_runtime_key
from .persistence_factory import build_paper_persistence
from .runtime_status import HostedRuntimeStatus

PAPER_CYCLE_POLL_SECONDS = 300.0


def _now_utc() -> str:
    return datetime.now(UTC).isoformat()


def _safe_cycle_reason(*, processed: int, remaining_backlog: bool) -> str:
    if remaining_backlog:
        return "catch-up pending"
    if processed:
        return f"processed {processed} bar(s)"
    return "no new eligible bar"


@app.command("paper-cycle")
def paper_cycle(
    symbol: str = typer.Option("GC=F", help="Yahoo Finance symbol"),
    period: str = typer.Option("5d", help="History period"),
    interval: str = typer.Option("5m", help="Bar interval"),
    max_catchup_bars: int = typer.Option(12, min=1),
) -> None:
    runtime_key = build_runtime_key(symbol, interval)
    starting_cash = RiskConfig().starting_cash
    try:
        backend = build_paper_persistence()
    except Exception as exc:  # noqa: BLE001 - sanitize provider errors at CLI boundary
        console.print(
            "Paper cycle: persistence initialization failed "
            f"({type(exc).__name__})"
        )
        raise typer.Exit(code=1) from None

    try:
        backend.save_runtime_status(
            runtime_key,
            HostedRuntimeStatus(
                engine_status="STARTING",
                symbol=symbol,
                interval=interval,
                updated_at_utc=_now_utc(),
                equity=starting_cash,
                poll_seconds=PAPER_CYCLE_POLL_SECONDS,
            ),
        )
        result = PaperCycleRunner(persistence=backend).run_once(
            symbol=symbol,
            period=period,
            interval=interval,
            max_catchup_bars=max_catchup_bars,
        )
        state = backend.load_runtime(runtime_key, starting_cash).state
        equity = state.cash + state.units * state.last_price
        reason = _safe_cycle_reason(
            processed=result.processed,
            remaining_backlog=result.remaining_backlog,
        )
        backend.save_runtime_status(
            runtime_key,
            HostedRuntimeStatus(
                engine_status="RUNNING",
                symbol=symbol,
                interval=interval,
                updated_at_utc=_now_utc(),
                last_cycle_timestamp=result.last_processed,
                processed=result.processed > 0,
                reason=reason,
                equity=equity,
                units=state.units,
                processed_bars=state.processed_bars,
                poll_seconds=PAPER_CYCLE_POLL_SECONDS,
            ),
        )
        console.print(
            f"Paper cycle: {reason}; processed_bars={state.processed_bars}"
        )
    except Exception as exc:
        try:
            backend.save_runtime_status(
                runtime_key,
                HostedRuntimeStatus(
                    engine_status="ERROR",
                    symbol=symbol,
                    interval=interval,
                    updated_at_utc=_now_utc(),
                    error=f"{type(exc).__name__}: worker failure",
                    poll_seconds=PAPER_CYCLE_POLL_SECONDS,
                ),
            )
        except Exception as status_exc:  # noqa: BLE001 - best-effort failure reporting
            console.print(
                "Paper cycle: ERROR status persistence failed "
                f"({type(status_exc).__name__})"
            )
        raise typer.Exit(code=1) from exc

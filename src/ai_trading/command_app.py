from __future__ import annotations

import typer

from .cli import app, console
from .paper_cycle_service import (
    PaperCycleServiceError,
    ProductionPaperCycleSettings,
    run_production_paper_cycle,
)

PAPER_CYCLE_POLL_SECONDS = 300.0


@app.command("paper-cycle")
def paper_cycle(
    symbol: str = typer.Option("GC=F", help="Yahoo Finance symbol"),
    period: str = typer.Option("5d", help="History period"),
    interval: str = typer.Option("5m", help="Bar interval"),
    max_catchup_bars: int = typer.Option(12, min=1),
) -> None:
    settings = ProductionPaperCycleSettings(
        symbol=symbol,
        period=period,
        interval=interval,
        max_catchup_bars=max_catchup_bars,
        poll_seconds=PAPER_CYCLE_POLL_SECONDS,
    )
    try:
        result = run_production_paper_cycle(settings)
    except PaperCycleServiceError as exc:
        console.print(f"Paper cycle: {exc.code} ({exc.error_type})")
        raise typer.Exit(code=1) from None

    console.print(
        f"Paper cycle: {result.reason}; processed_bars={result.processed_bars}"
    )

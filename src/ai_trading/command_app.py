from __future__ import annotations

import typer

from .cli import app, console
from .paper_cycle import DEFAULT_MAX_CATCHUP_BARS
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
    max_catchup_bars: int = typer.Option(DEFAULT_MAX_CATCHUP_BARS, min=1),
    shadow_challenger: bool = typer.Option(
        False,
        "--shadow-challenger/--no-shadow-challenger",
    ),
) -> None:
    settings = ProductionPaperCycleSettings(
        symbol=symbol,
        period=period,
        interval=interval,
        max_catchup_bars=max_catchup_bars,
        poll_seconds=PAPER_CYCLE_POLL_SECONDS,
        shadow_challenger_enabled=shadow_challenger,
    )
    try:
        result = run_production_paper_cycle(settings)
    except PaperCycleServiceError as exc:
        console.print(f"Paper cycle: {exc.code} ({exc.error_type})")
        raise typer.Exit(code=1) from None

    console.print(
        f"Paper cycle: {result.reason}; processed_bars={result.processed_bars}"
    )


@app.command("turnover-study")
def turnover_study(
    symbols: str = typer.Option("GC=F,^GDAXI,BTC-USD"),
    period: str = typer.Option("1mo"),
    interval: str = typer.Option("5m"),
    max_bars: int = typer.Option(2400, min=800, max=20000),
    output: str = typer.Option("artifacts/turnover-study.json"),
) -> None:
    """Compare paper turnover thresholds offline; never change runtime settings."""
    import json
    from hashlib import sha256
    from pathlib import Path

    from .data import load_history
    from .execution_costs import risk_config_for_symbol
    from .paper_cycle import _completed_market_bars
    from .turnover_study import compare_rebalance_thresholds

    names = tuple(s.strip() for s in symbols.split(",") if s.strip())
    if not names or len(set(names)) != len(names):
        raise typer.BadParameter("symbols must be non-empty and unique")
    results: list[dict[str, object]] = []
    failures: list[dict[str, str]] = []
    for symbol in names:
        try:
            market = _completed_market_bars(
                load_history(symbol, period, interval),
                interval=interval,
            ).tail(max_bars)
            result = compare_rebalance_thresholds(
                symbol,
                market,
                risk_config=risk_config_for_symbol(symbol),
            )
            result["history_sha256"] = sha256(
                market.to_csv().encode("utf-8")
            ).hexdigest()
            results.append(result)
            console.print(
                f"{symbol}: baseline={result['trials'][0]['full_net_return']:.2%}; "
                f"validation_candidate={result['validation_selected_threshold']}; "
                f"holdout_passed={result['holdout_passed']}"
            )
        except Exception as exc:  # noqa: BLE001 - report missing provider evidence
            failures.append({"symbol": symbol, "error_type": type(exc).__name__})
            console.print(f"{symbol}: unavailable ({type(exc).__name__})")

    payload = {
        "method": "purged-walk-forward-proxy-validation-then-holdout",
        "source": "Yahoo Finance",
        "period": period,
        "interval": interval,
        "max_bars_per_market": max_bars,
        "results": results,
        "failures": failures,
        "changes_paper_settings": False,
        "changes_live_settings": False,
    }
    destination = Path(output)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(
        json.dumps(payload, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    console.print(f"Research report saved: {destination}")
    if failures:
        raise typer.Exit(code=1)


if __name__ == "__main__":
    app()

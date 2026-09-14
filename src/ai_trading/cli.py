from __future__ import annotations

import typer
from rich.console import Console
from rich.table import Table

from .backtest import WalkForwardBacktester, WalkForwardConfig
from .config import ModelConfig, RiskConfig
from .data import load_history
from .engine import TradingEngine
from .experiments import ExperimentRegistry

app = typer.Typer(help="Autonomous trading research CLI")
console = Console()


@app.command()
def train(
    symbol: str = typer.Option("GC=F", help="Yahoo Finance symbol"),
    period: str = typer.Option("5y", help="History period"),
    interval: str = typer.Option("1d", help="Bar interval"),
) -> None:
    df = load_history(symbol, period, interval)
    engine = TradingEngine()
    engine.train(df)
    console.print(f"Model trained on {len(df)} bars for {symbol}.")


@app.command()
def paper(
    symbol: str = typer.Option("GC=F", help="Yahoo Finance symbol"),
    period: str = typer.Option("5y", help="History period"),
    interval: str = typer.Option("1d", help="Bar interval"),
) -> None:
    df = load_history(symbol, period, interval)
    result = TradingEngine().paper_run(df)

    table = Table(title=f"Paper backtest: {symbol}")
    table.add_column("Metric")
    table.add_column("Value", justify="right")
    table.add_row("Starting equity", f"{result.starting_equity:,.2f}")
    table.add_row("Final equity", f"{result.final_equity:,.2f}")
    table.add_row("Total return", f"{result.total_return:.2%}")
    table.add_row("Max drawdown", f"{result.max_drawdown:.2%}")
    table.add_row("Trades", str(result.trades))
    table.add_row("Decisions", str(result.decisions))
    console.print(table)


@app.command("walk-forward")
def walk_forward(
    symbol: str = typer.Option("GC=F", help="Yahoo Finance symbol"),
    period: str = typer.Option("10y", help="History period"),
    interval: str = typer.Option("1d", help="Bar interval"),
    min_train_bars: int = typer.Option(252, min=50),
    test_window_bars: int = typer.Option(63, min=5),
    max_train_bars: int = typer.Option(1000, min=100),
    save_experiment: bool = typer.Option(True, "--save/--no-save"),
) -> None:
    df = load_history(symbol, period, interval)
    risk_config = RiskConfig()
    model_config = ModelConfig()
    wf_config = WalkForwardConfig(
        min_train_bars=min_train_bars,
        test_window_bars=test_window_bars,
        max_train_bars=max_train_bars,
    )
    report = WalkForwardBacktester(
        risk_config=risk_config,
        model_config=model_config,
        config=wf_config,
    ).run(df)

    table = Table(title=f"Walk-forward: {symbol}")
    table.add_column("Metric")
    table.add_column("Strategy", justify="right")
    table.add_column("Buy & hold", justify="right")
    table.add_row(
        "Total return",
        f"{report.metrics.total_return:.2%}",
        f"{report.benchmark_metrics.total_return:.2%}",
    )
    table.add_row(
        "Annualized return",
        f"{report.metrics.annualized_return:.2%}",
        f"{report.benchmark_metrics.annualized_return:.2%}",
    )
    table.add_row(
        "Sharpe",
        f"{report.metrics.sharpe:.3f}",
        f"{report.benchmark_metrics.sharpe:.3f}",
    )
    table.add_row(
        "Sortino",
        f"{report.metrics.sortino:.3f}",
        f"{report.benchmark_metrics.sortino:.3f}",
    )
    table.add_row(
        "Max drawdown",
        f"{report.metrics.max_drawdown:.2%}",
        f"{report.benchmark_metrics.max_drawdown:.2%}",
    )
    table.add_row(
        "Calmar",
        f"{report.metrics.calmar:.3f}",
        f"{report.benchmark_metrics.calmar:.3f}",
    )
    console.print(table)
    console.print(
        f"folds={report.folds} trades={report.trades} "
        f"decisions={report.decisions} rejected={report.rejected_decisions} "
        f"excess_return={report.excess_return:.2%}"
    )

    if save_experiment:
        ExperimentRegistry().append(
            name="walk-forward",
            symbol=symbol,
            config={
                "period": period,
                "interval": interval,
                "walk_forward": wf_config.as_dict(),
                "risk": risk_config.__dict__,
                "model": model_config.__dict__,
            },
            metrics=report.metrics,
            metadata={
                "benchmark": report.benchmark_metrics.as_dict(),
                "excess_return": report.excess_return,
                "folds": report.folds,
                "trades": report.trades,
                "decisions": report.decisions,
                "rejected_decisions": report.rejected_decisions,
            },
        )
        console.print("Experiment saved to artifacts/experiments.jsonl")


if __name__ == "__main__":
    app()

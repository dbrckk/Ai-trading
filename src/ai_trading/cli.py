from __future__ import annotations

import typer
from rich.console import Console
from rich.table import Table

from .backtest import WalkForwardBacktester, WalkForwardConfig
from .config import ModelConfig, RiskConfig
from .data import load_history
from .engine import TradingEngine
from .experiments import ExperimentRegistry
from .promotion import evaluate_challenger
from .robustness import block_bootstrap_returns
from .tuning import tune_walk_forward

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


@app.command("compare-models")
def compare_models(
    symbol: str = typer.Option("GC=F", help="Yahoo Finance symbol"),
    period: str = typer.Option("10y", help="History period"),
    interval: str = typer.Option("1d", help="Bar interval"),
    min_train_bars: int = typer.Option(252, min=100),
    test_window_bars: int = typer.Option(63, min=10),
    max_train_bars: int = typer.Option(1000, min=150),
) -> None:
    df = load_history(symbol, period, interval)
    risk_config = RiskConfig()
    model_config = ModelConfig()

    baseline_cfg = WalkForwardConfig(
        min_train_bars=min_train_bars,
        test_window_bars=test_window_bars,
        max_train_bars=max_train_bars,
        use_ensemble=False,
    )
    ensemble_cfg = WalkForwardConfig(
        min_train_bars=min_train_bars,
        test_window_bars=test_window_bars,
        max_train_bars=max_train_bars,
        use_ensemble=True,
    )

    baseline = WalkForwardBacktester(
        risk_config=risk_config,
        model_config=model_config,
        config=baseline_cfg,
    ).run(df)
    ensemble = WalkForwardBacktester(
        risk_config=risk_config,
        model_config=model_config,
        config=ensemble_cfg,
    ).run(df)

    decision = evaluate_challenger(baseline.metrics, ensemble.metrics)

    table = Table(title=f"Champion vs challenger: {symbol}")
    table.add_column("Metric")
    table.add_column("Baseline", justify="right")
    table.add_column("Ensemble", justify="right")
    table.add_row(
        "Total return",
        f"{baseline.metrics.total_return:.2%}",
        f"{ensemble.metrics.total_return:.2%}",
    )
    table.add_row(
        "Sharpe",
        f"{baseline.metrics.sharpe:.3f}",
        f"{ensemble.metrics.sharpe:.3f}",
    )
    table.add_row(
        "Sortino",
        f"{baseline.metrics.sortino:.3f}",
        f"{ensemble.metrics.sortino:.3f}",
    )
    table.add_row(
        "Max drawdown",
        f"{baseline.metrics.max_drawdown:.2%}",
        f"{ensemble.metrics.max_drawdown:.2%}",
    )
    table.add_row(
        "Calmar",
        f"{baseline.metrics.calmar:.3f}",
        f"{ensemble.metrics.calmar:.3f}",
    )
    console.print(table)
    console.print(
        f"Promotion: {'YES' if decision.promote else 'NO'} — {decision.reason}"
    )


@app.command("robustness")
def robustness(
    symbol: str = typer.Option("GC=F", help="Yahoo Finance symbol"),
    period: str = typer.Option("10y", help="History period"),
    interval: str = typer.Option("1d", help="Bar interval"),
    simulations: int = typer.Option(1000, min=100),
    block_size: int = typer.Option(5, min=1),
) -> None:
    df = load_history(symbol, period, interval)
    report = WalkForwardBacktester(
        risk_config=RiskConfig(),
        model_config=ModelConfig(),
        config=WalkForwardConfig(use_ensemble=True),
    ).run(df)
    bootstrap = block_bootstrap_returns(
        report.equity_curve,
        simulations=simulations,
        block_size=block_size,
    )

    table = Table(title=f"Robustness bootstrap: {symbol}")
    table.add_column("Metric")
    table.add_column("Value", justify="right")
    table.add_row("Median return", f"{bootstrap.median_return:.2%}")
    table.add_row("5th percentile", f"{bootstrap.p05_return:.2%}")
    table.add_row("95th percentile", f"{bootstrap.p95_return:.2%}")
    table.add_row("P(return > 0)", f"{bootstrap.probability_positive:.2%}")
    table.add_row("P(loss > 10%)", f"{bootstrap.probability_loss_gt_10pct:.2%}")
    console.print(table)


@app.command("tune")
def tune(
    symbol: str = typer.Option("GC=F", help="Yahoo Finance symbol"),
    period: str = typer.Option("10y", help="History period"),
    interval: str = typer.Option("1d", help="Bar interval"),
    trials: int = typer.Option(20, min=1, max=500),
) -> None:
    df = load_history(symbol, period, interval)
    result = tune_walk_forward(df, trials=trials, use_ensemble=True)

    table = Table(title=f"Optuna tuning: {symbol}")
    table.add_column("Field")
    table.add_column("Value", justify="right")
    table.add_row("Best score", f"{result.best_score:.6f}")
    table.add_row("Trials", str(result.trials))
    for key, value in sorted(result.best_params.items()):
        table.add_row(key, f"{value:.6g}")
    console.print(table)


if __name__ == "__main__":
    app()

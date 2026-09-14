from __future__ import annotations

import pandas as pd
import typer
from rich.console import Console
from rich.table import Table

from .backtest import WalkForwardBacktester, WalkForwardConfig
from .champions import ChampionRegistry
from .config import ModelConfig, RiskConfig
from .continuous import run_learning_cycle
from .data import load_history
from .drift import detect_drift
from .engine import TradingEngine
from .experiments import ExperimentRegistry
from .expert_factory import FactoryConfig, run_expert_factory
from .expert_pool import ExpertPoolStore, ExpertRecord, reconcile_pool
from .expert_pool_manager import refresh_expert_pool
from .expert_sandbox import validate_specialist
from .features import make_features
from .guardrails import evaluate_health
from .multiasset_backtest import MultiAssetWalkForwardBacktester
from .multiasset_runtime import MultiAssetPaperRuntime
from .orchestrator import AutonomousPaperOrchestrator
from .performance import PerformanceMetrics
from .portfolio import AllocationConfig, inverse_volatility_weights, target_notionals
from .portfolio_risk import PortfolioRiskConfig, evaluate_portfolio_risk
from .promotion import evaluate_challenger
from .readiness import evaluate_readiness
from .regime_validation import validate_regime_returns
from .robustness import block_bootstrap_returns
from .runtime import PaperAutonomousRuntime
from .scheduler import PaperScheduler, SchedulerConfig
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


@app.command("health-check")
def health_check(
    symbol: str = typer.Option("GC=F", help="Yahoo Finance symbol"),
    period: str = typer.Option("10y", help="History period"),
    interval: str = typer.Option("1d", help="Bar interval"),
    rollback: bool = typer.Option(False, "--rollback/--no-rollback"),
) -> None:
    df = load_history(symbol, period, interval)
    report = WalkForwardBacktester(
        risk_config=RiskConfig(),
        model_config=ModelConfig(),
        config=WalkForwardConfig(use_ensemble=True),
    ).run(df)

    features = make_features(df).dropna()
    split = max(60, int(len(features) * 0.75))
    reference_features = features.iloc[:split]
    recent_features = features.iloc[split:]

    strategy_returns = report.equity_curve.pct_change().dropna()
    return_split = max(20, int(len(strategy_returns) * 0.75))
    drift = detect_drift(
        reference_features,
        recent_features,
        strategy_returns.iloc[:return_split],
        strategy_returns.iloc[return_split:],
    )
    regime_check = validate_regime_returns(report.regime_returns)
    health = evaluate_health(report.metrics, drift)

    table = Table(title=f"Health check: {symbol}")
    table.add_column("Check")
    table.add_column("Value", justify="right")
    table.add_row("Healthy", "YES" if health.healthy else "NO")
    table.add_row("Rollback advised", "YES" if health.rollback else "NO")
    table.add_row("Health reason", health.reason)
    table.add_row("Feature drift score", f"{drift.feature_drift_score:.3f}")
    table.add_row("Return drift score", f"{drift.return_drift_score:.3f}")
    table.add_row("Regime validation", "PASS" if regime_check.valid else "FAIL")
    table.add_row("Regimes covered", str(regime_check.covered_regimes))
    table.add_row("Worst regime return", f"{regime_check.worst_regime_return:.2%}")
    console.print(table)

    if rollback and (health.rollback or not regime_check.valid):
        registry = ChampionRegistry()
        active = registry.active()
        if active is None:
            console.print("Rollback unavailable: no active champion registry entry.")
            raise typer.Exit(code=2)
        try:
            restored = registry.rollback()
        except RuntimeError as exc:
            console.print(f"Rollback unavailable: {exc}")
            raise typer.Exit(code=2) from exc
        console.print(f"Rolled back to champion {restored.version} ({restored.model_name}).")


@app.command("learning-cycle")
def learning_cycle(
    symbol: str = typer.Option("GC=F", help="Yahoo Finance symbol"),
    period: str = typer.Option("10y", help="History period"),
    interval: str = typer.Option("1d", help="Bar interval"),
    trials: int = typer.Option(10, min=1, max=200),
) -> None:
    df = load_history(symbol, period, interval)
    registry = ChampionRegistry()
    active = registry.active()

    if active is None:
        baseline = WalkForwardBacktester(
            risk_config=RiskConfig(),
            model_config=ModelConfig(),
            config=WalkForwardConfig(use_ensemble=False),
        ).run(df)
        champion_metrics = baseline.metrics
    else:
        champion_metrics = PerformanceMetrics(**active.metrics)

    result = run_learning_cycle(
        df,
        symbol=symbol,
        champion_metrics=champion_metrics,
        registry=registry,
        trials=trials,
    )

    table = Table(title=f"Learning cycle: {symbol}")
    table.add_column("Check")
    table.add_column("Value", justify="right")
    table.add_row("Tuning score", f"{result.tuning.best_score:.6f}")
    table.add_row("Promotion policy", "PASS" if result.promotion.promote else "FAIL")
    table.add_row("Regime validation", "PASS" if result.regime_validation.valid else "FAIL")
    table.add_row(
        "Bootstrap P(return > 0)",
        f"{result.robustness.probability_positive:.2%}",
    )
    table.add_row("5th percentile return", f"{result.robustness.p05_return:.2%}")
    table.add_row("Promoted", "YES" if result.promoted else "NO")
    table.add_row("Champion version", result.champion_version or "-")
    console.print(table)


@app.command("runtime-step")
def runtime_step(
    symbol: str = typer.Option("GC=F", help="Yahoo Finance symbol"),
    period: str = typer.Option("1y", help="History period"),
    interval: str = typer.Option("1d", help="Bar interval"),
    learning_cycle_every_bars: int = typer.Option(63, min=1),
) -> None:
    df = load_history(symbol, period, interval)
    result = PaperAutonomousRuntime(
        learning_cycle_every_bars=learning_cycle_every_bars,
    ).step(df)

    table = Table(title=f"Autonomous paper runtime: {symbol}")
    table.add_column("Field")
    table.add_column("Value", justify="right")
    table.add_row("Processed", "YES" if result.processed else "NO")
    table.add_row("Timestamp", result.timestamp or "-")
    table.add_row("Side", str(result.side))
    table.add_row("Confidence", f"{result.confidence:.3f}")
    table.add_row("Risk approved", "YES" if result.approved else "NO")
    table.add_row("Reason", result.reason)
    table.add_row("Equity", f"{result.equity:,.2f}")
    table.add_row("Units", f"{result.units:.6f}")
    table.add_row("Processed bars", str(result.processed_bars))
    table.add_row("Learning cycle due", "YES" if result.retrain_due else "NO")
    console.print(table)


@app.command("paper-loop")
def paper_loop(
    symbol: str = typer.Option("GC=F", help="Yahoo Finance symbol"),
    period: str = typer.Option("1y", help="History period"),
    interval: str = typer.Option("1d", help="Bar interval"),
    poll_seconds: float = typer.Option(60.0, min=0.0),
    iterations: int = typer.Option(1, min=1, help="Number of scheduler iterations"),
    learning_trials: int = typer.Option(10, min=1, max=200),
) -> None:
    orchestrator = AutonomousPaperOrchestrator(
        learning_trials=learning_trials,
    )
    scheduler = PaperScheduler(
        orchestrator=orchestrator,
        data_loader=lambda: load_history(symbol, period, interval),
        symbol=symbol,
        config=SchedulerConfig(
            poll_seconds=poll_seconds,
            max_iterations=iterations,
        ),
    )
    results = scheduler.run()
    last = results[-1]

    table = Table(title=f"Autonomous paper loop: {symbol}")
    table.add_column("Field")
    table.add_column("Value", justify="right")
    table.add_row("Iterations", str(len(results)))
    table.add_row("Last processed", "YES" if last.runtime.processed else "NO")
    table.add_row("Equity", f"{last.runtime.equity:,.2f}")
    table.add_row("Units", f"{last.runtime.units:.6f}")
    table.add_row(
        "Learning cycle triggered",
        "YES" if last.learning_cycle_triggered else "NO",
    )
    table.add_row("Trigger reason", last.trigger_reason or "-")
    if last.learning_cycle is not None:
        table.add_row(
            "Promoted",
            "YES" if last.learning_cycle.promoted else "NO",
        )
        table.add_row(
            "Champion version",
            last.learning_cycle.champion_version or "-",
        )
    console.print(table)


@app.command("portfolio-analyze")
def portfolio_analyze(
    symbols: str = typer.Option("GC=F,SI=F,CL=F", help="Comma-separated Yahoo symbols"),
    period: str = typer.Option("2y", help="History period"),
    interval: str = typer.Option("1d", help="Bar interval"),
    equity: float = typer.Option(100_000.0, min=1.0),
) -> None:
    names = [s.strip() for s in symbols.split(",") if s.strip()]
    if len(names) < 2:
        raise typer.BadParameter("Provide at least two symbols")

    closes = {}
    for name in names:
        df = load_history(name, period, interval)
        closes[name] = df["Close"].astype(float)

    close_frame = pd.DataFrame(closes).dropna()
    returns = close_frame.pct_change().dropna()
    weights = inverse_volatility_weights(
        returns,
        AllocationConfig(max_asset_weight=0.35, target_gross_exposure=1.0),
    )
    notionals = target_notionals(equity, weights)
    risk = evaluate_portfolio_risk(
        notionals,
        equity,
        returns,
        PortfolioRiskConfig(),
    )

    table = Table(title="Multi-asset portfolio analysis")
    table.add_column("Asset")
    table.add_column("Weight", justify="right")
    table.add_column("Target notional", justify="right")
    for name in weights.index:
        table.add_row(name, f"{weights[name]:.2%}", f"{notionals[name]:,.2f}")
    console.print(table)
    console.print(
        f"Portfolio risk: {'PASS' if risk.approved else 'FAIL'} | "
        f"gross={risk.gross_exposure:.2f} net={risk.net_exposure:.2f} "
        f"max_asset={risk.max_asset_exposure:.2f} max_corr={risk.max_pair_correlation:.2f}"
    )
    if risk.reasons:
        console.print("; ".join(risk.reasons))


@app.command("readiness-check")
def readiness_check(
    symbol: str = typer.Option("GC=F", help="Yahoo Finance symbol"),
    period: str = typer.Option("10y", help="History period"),
    interval: str = typer.Option("1d", help="Bar interval"),
    burn_in_bars: int = typer.Option(126, min=1),
    scheduler_errors: int = typer.Option(0, min=0),
) -> None:
    df = load_history(symbol, period, interval)
    report = WalkForwardBacktester(
        risk_config=RiskConfig(),
        model_config=ModelConfig(),
        config=WalkForwardConfig(use_ensemble=True),
    ).run(df)
    bootstrap = block_bootstrap_returns(report.equity_curve)
    readiness = evaluate_readiness(
        metrics=report.metrics,
        burn_in_bars=burn_in_bars,
        bootstrap_probability_positive=bootstrap.probability_positive,
        regimes_covered=len(report.regime_returns),
        scheduler_errors=scheduler_errors,
    )

    table = Table(title=f"Paper readiness: {symbol}")
    table.add_column("Field")
    table.add_column("Value", justify="right")
    table.add_row("Ready", "YES" if readiness.ready else "NO")
    table.add_row("Checks passed", f"{readiness.checks_passed}/{readiness.checks_total}")
    table.add_row("Sharpe", f"{report.metrics.sharpe:.3f}")
    table.add_row("Sortino", f"{report.metrics.sortino:.3f}")
    table.add_row("Max drawdown", f"{report.metrics.max_drawdown:.2%}")
    table.add_row("Bootstrap P(return > 0)", f"{bootstrap.probability_positive:.2%}")
    table.add_row("Regimes covered", str(len(report.regime_returns)))
    console.print(table)
    if readiness.reasons:
        console.print("; ".join(readiness.reasons))


@app.command("multiasset-step")
def multiasset_step(
    symbols: str = typer.Option("GC=F,SI=F,CL=F", help="Comma-separated Yahoo symbols"),
    period: str = typer.Option("1y", help="History period"),
    interval: str = typer.Option("1d", help="Bar interval"),
) -> None:
    names = [s.strip() for s in symbols.split(",") if s.strip()]
    if len(names) < 2:
        raise typer.BadParameter("Provide at least two symbols")

    markets = {name: load_history(name, period, interval) for name in names}
    result = MultiAssetPaperRuntime().step(markets)

    table = Table(title="Multi-asset paper runtime")
    table.add_column("Field")
    table.add_column("Value", justify="right")
    table.add_row("Processed", "YES" if result.processed else "NO")
    table.add_row("Timestamp", result.timestamp or "-")
    table.add_row("Equity", f"{result.equity:,.2f}")
    table.add_row("Cash", f"{result.cash:,.2f}")
    table.add_row("Risk approved", "YES" if result.risk_approved else "NO")
    console.print(table)

    if result.weights:
        weights_table = Table(title="Target allocation")
        weights_table.add_column("Asset")
        weights_table.add_column("Weight", justify="right")
        weights_table.add_column("Notional", justify="right")
        weights_table.add_column("Signal", justify="right")
        weights_table.add_column("Confidence", justify="right")
        for name in sorted(result.weights):
            weights_table.add_row(
                name,
                f"{result.weights[name]:.2%}",
                f"{result.notionals[name]:,.2f}",
                str(result.signals.get(name, 0)),
                f"{result.confidences.get(name, 0.0):.3f}",
            )
        console.print(weights_table)

    if result.risk_reasons:
        console.print("; ".join(result.risk_reasons))


@app.command("multiasset-backtest")
def multiasset_backtest(
    symbols: str = typer.Option("GC=F,SI=F,CL=F", help="Comma-separated Yahoo symbols"),
    period: str = typer.Option("10y", help="History period"),
    interval: str = typer.Option("1d", help="Bar interval"),
) -> None:
    names = [s.strip() for s in symbols.split(",") if s.strip()]
    if len(names) < 2:
        raise typer.BadParameter("Provide at least two symbols")

    markets = {name: load_history(name, period, interval) for name in names}
    report = MultiAssetWalkForwardBacktester().run(markets)

    table = Table(title="Multi-asset walk-forward")
    table.add_column("Metric")
    table.add_column("Value", justify="right")
    table.add_row("Total return", f"{report.metrics.total_return:.2%}")
    table.add_row("Annualized return", f"{report.metrics.annualized_return:.2%}")
    table.add_row("Sharpe", f"{report.metrics.sharpe:.3f}")
    table.add_row("Sortino", f"{report.metrics.sortino:.3f}")
    table.add_row("Max drawdown", f"{report.metrics.max_drawdown:.2%}")
    table.add_row("Calmar", f"{report.metrics.calmar:.3f}")
    table.add_row("Trades", str(report.trades))
    table.add_row("Decisions", str(report.decisions))
    table.add_row("Rejected rebalances", str(report.rejected_rebalances))
    console.print(table)


@app.command("expert-sandbox")
def expert_sandbox(
    symbol: str = typer.Option("GC=F", help="Yahoo Finance symbol"),
    kind: str = typer.Option("trend", help="trend, range, or high_vol"),
    period: str = typer.Option("5y", help="History period"),
    interval: str = typer.Option("1d", help="Bar interval"),
) -> None:
    if kind not in {"trend", "range", "high_vol"}:
        raise typer.BadParameter("kind must be trend, range, or high_vol")

    df = load_history(symbol, period, interval)
    result = validate_specialist(df, kind=kind)

    pool = ExpertPoolStore()
    name = f"{symbol}:{kind}"
    pool.upsert(
        ExpertRecord(
            name=name,
            kind=kind,
            status="challenger",
            score=result.validation_score,
            validation_score=result.validation_score,
            observations=result.observations,
            compute_cost=1.0,
        )
    )
    reconciled = reconcile_pool(pool.load())
    pool.save(reconciled)
    record = reconciled[name]

    table = Table(title=f"Expert sandbox: {name}")
    table.add_column("Metric")
    table.add_column("Value", justify="right")
    table.add_row("Status", record.status)
    table.add_row("Validation score", f"{result.validation_score:.3f}")
    table.add_row("Accuracy", f"{result.accuracy:.3f}")
    table.add_row("Sharpe", f"{result.metrics.sharpe:.3f}")
    table.add_row("Sortino", f"{result.metrics.sortino:.3f}")
    table.add_row("Max drawdown", f"{result.metrics.max_drawdown:.2%}")
    table.add_row("Observations", str(result.observations))
    console.print(table)


@app.command("expert-pool-refresh")
def expert_pool_refresh(
    symbol: str = typer.Option("GC=F", help="Yahoo Finance symbol"),
    period: str = typer.Option("5y", help="History period"),
    interval: str = typer.Option("1d", help="Bar interval"),
) -> None:
    df = load_history(symbol, period, interval)
    result = refresh_expert_pool(df, symbol=symbol)

    table = Table(title=f"Expert pool refresh: {symbol}")
    table.add_column("Expert")
    table.add_column("Status")
    table.add_column("Score", justify="right")
    table.add_column("Validation", justify="right")
    table.add_column("Obs", justify="right")

    for name, record in sorted(result.records.items()):
        if not name.startswith(f"{symbol}:"):
            continue
        table.add_row(
            name,
            record.status,
            f"{record.score:.3f}",
            f"{record.validation_score:.3f}",
            str(record.observations),
        )
    console.print(table)


@app.command("expert-factory-run")
def expert_factory_run(
    symbol: str = typer.Option("GC=F", help="Yahoo Finance symbol"),
    period: str = typer.Option("5y", help="History period"),
    interval: str = typer.Option("1d", help="Bar interval"),
    max_candidates: int = typer.Option(12, min=1, max=50),
    max_promotions: int = typer.Option(3, min=0, max=10),
) -> None:
    df = load_history(symbol, period, interval)
    result = run_expert_factory(
        df,
        symbol=symbol,
        config=FactoryConfig(
            max_candidates=max_candidates,
            max_promotions_per_run=max_promotions,
        ),
    )

    table = Table(title=f"Expert factory: {symbol}")
    table.add_column("Field")
    table.add_column("Value", justify="right")
    table.add_row("Evaluated", str(result.evaluated))
    table.add_row("Promoted", str(result.promoted))
    table.add_row("Generated candidates", str(len(result.candidates)))
    console.print(table)


if __name__ == "__main__":
    app()

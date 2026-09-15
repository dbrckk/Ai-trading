from __future__ import annotations

import json
import os
import sys
from dataclasses import asdict
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path

import numpy as np
import pandas as pd
import typer
from rich.console import Console
from rich.table import Table

from .allocator_config_store import AllocatorConfigStore
from .allocator_tuning import tune_global_allocator
from .audit_chain import verify_audit_chain
from .audit_integrity import verify_jsonl_audit
from .backtest import WalkForwardBacktester, WalkForwardConfig
from .benchmark_gate import evaluate_benchmark_gate
from .bootstrap_gate import evaluate_bootstrap_gate
from .bootstrap_robustness import bootstrap_equity_curve
from .champions import ChampionRegistry
from .chaos import ChaosScenario
from .config import ModelConfig, RiskConfig
from .continuous import run_learning_cycle
from .control_plane import read_control_plane
from .cost_stress import run_cost_stress
from .cost_stress_gate import evaluate_cost_stress_gate
from .crisis_controller import limits_for_state
from .crisis_state_store import CrisisStateStore
from .data import load_history
from .dataset_evidence import build_dataset_evidence
from .deployment_readiness import DeploymentReadinessPolicy, evaluate_deployment_readiness
from .drift import detect_drift
from .engine import TradingEngine
from .evolution_manager import run_evolution_cycle
from .experiments import ExperimentRegistry
from .expert_factory import FactoryConfig, run_expert_factory
from .expert_pool import ExpertPoolStore, ExpertRecord, reconcile_pool
from .expert_pool_manager import refresh_expert_pool
from .expert_sandbox import validate_specialist
from .features import make_features
from .generation_rollback import rollback_generation
from .generations import GenerationStore
from .global_allocator import GlobalAllocatorConfig, allocate_global_capital
from .governor_state_store import GovernorStateStore
from .guardrails import evaluate_health
from .health_server import HealthServer
from .lifecycle_log import LifecycleEventLog
from .maintenance import MaintenanceState, MaintenanceStore
from .metrics import collect_metrics, prometheus_text
from .multiasset_backtest import MultiAssetWalkForwardBacktester
from .multiasset_evolution import run_multiasset_evolution_cycle
from .multiasset_runtime import MultiAssetPaperRuntime
from .multiasset_scheduler import MultiAssetPaperScheduler, MultiAssetSchedulerConfig
from .orchestrator import AutonomousPaperOrchestrator
from .parameter_sensitivity import run_parameter_sensitivity
from .performance import PerformanceMetrics
from .portfolio import AllocationConfig, inverse_volatility_weights, target_notionals
from .portfolio_risk import PortfolioRiskConfig, evaluate_portfolio_risk
from .promotion import evaluate_challenger
from .qualification_store import QualificationStore
from .qualification_suite import run_qualification_suite
from .quantitative_artifact import (
    build_quantitative_artifact,
    load_quantitative_artifact,
    save_quantitative_artifact,
)
from .quantitative_qualification import evaluate_quantitative_qualification
from .readiness import evaluate_readiness
from .readiness_release import (
    ReadinessReleaseStore,
    create_readiness_release,
    verify_readiness_release,
)
from .readiness_revocation import ReadinessRevocationStore
from .readiness_score import ReadinessHistoryStore
from .readiness_trend import evaluate_readiness_trend
from .regime_gate import evaluate_regime_gate
from .regime_validation import validate_regime_returns
from .reliability import evaluate_reliability
from .reproducibility import verify_quantitative_reproducibility
from .resilience import ResilienceStateStore
from .robustness import block_bootstrap_returns
from .runtime import PaperAutonomousRuntime
from .runtime_factory import isolated_multiasset_runtime
from .scheduler import PaperScheduler, SchedulerConfig
from .sensitivity_gate import evaluate_sensitivity_gate
from .soak import run_multiasset_soak
from .soak_gate import evaluate_soak_qualification
from .state_snapshot import AtomicSnapshotStore
from .supervisor import PaperSupervisor, SupervisorConfig
from .supervisor_lease import SupervisorLeaseStore
from .tuning import tune_walk_forward
from .watchdog import HeartbeatStore, WatchdogPolicy, heartbeat_is_stale
from .watchdog_enforcer import enforce_watchdog

app = typer.Typer(help="Autonomous trading research CLI")
console = Console()


@app.command("self-test")
def self_test(
    workspace: str = typer.Option("artifacts/self-test"),
) -> None:
    root = Path(workspace)
    runtime = isolated_multiasset_runtime(root)

    def synthetic_market(seed: int, n: int = 180) -> pd.DataFrame:
        rng = np.random.default_rng(seed)
        index = pd.date_range("2025-01-01", periods=n, freq="D")
        returns = rng.normal(0.0003, 0.01, n)
        close = 100.0 * np.cumprod(1.0 + returns)
        open_ = close * (1.0 + rng.normal(0.0, 0.001, n))
        return pd.DataFrame(
            {
                "Open": open_,
                "High": np.maximum(open_, close) * 1.005,
                "Low": np.minimum(open_, close) * 0.995,
                "Close": close,
                "Volume": 1000.0 + np.arange(n),
            },
            index=index,
        )

    markets = {
        "GC=F": synthetic_market(1),
        "SI=F": synthetic_market(2),
        "CL=F": synthetic_market(3),
    }
    scheduler = MultiAssetPaperScheduler(
        runtime=runtime,
        data_loader=lambda: markets,
        config=MultiAssetSchedulerConfig(
            poll_seconds=0.0,
            max_iterations=1,
            max_consecutive_errors=1,
            snapshot_every_iterations=1,
            verify_audit_every_iterations=1,
        ),
        heartbeat_store=HeartbeatStore(root / "heartbeat.json"),
        snapshot_store=AtomicSnapshotStore(root / "snapshots"),
    )

    try:
        results = scheduler.run()
    except Exception as exc:
        console.print(f"SELF-TEST FAILED: {exc}")
        raise typer.Exit(code=1) from exc

    if len(results) != 1 or not results[0].processed:
        console.print("SELF-TEST FAILED: runtime did not process the synthetic bar set")
        raise typer.Exit(code=1)

    snapshot = scheduler.snapshot_store.latest_valid()
    if snapshot is None:
        console.print("SELF-TEST FAILED: no valid snapshot created")
        raise typer.Exit(code=1)

    table = Table(title="Ai-trading self-test")
    table.add_column("Check")
    table.add_column("Result", justify="right")
    table.add_row("Runtime step", "PASS")
    table.add_row("Equity", f"{results[0].equity:,.2f}")
    table.add_row("Governor", runtime.governor_state_store.load().verdict)
    table.add_row("Resilience", runtime.resilience_state_store.load().mode)
    table.add_row("Audit", "PASS" if runtime.audit.path.exists() else "FAIL")
    table.add_row("Snapshot", "PASS")
    table.add_row("Heartbeat", "PASS" if (root / "heartbeat.json").exists() else "FAIL")
    console.print(table)
    console.print(f"SELF-TEST PASS: workspace={root}")


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
    qualification_artifact: str = typer.Option(
        "artifacts/quantitative_qualification.json"
    ),
) -> None:
    df = load_history(symbol, period, interval)
    risk_config = RiskConfig()
    model_config = ModelConfig()
    wf_config = WalkForwardConfig(
        min_train_bars=min_train_bars,
        test_window_bars=test_window_bars,
        max_train_bars=max_train_bars,
    )
    backtester = WalkForwardBacktester(
        risk_config=risk_config,
        model_config=model_config,
        config=wf_config,
    )
    report = backtester.run(df)

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

    gate = evaluate_benchmark_gate(report)
    console.print(
        "Benchmark gate: "
        + ("PASS" if gate.passed else "FAIL")
    )
    if gate.reasons:
        for reason in gate.reasons:
            console.print(f"- {reason}")

    regime_gate = evaluate_regime_gate(report)
    console.print(
        "Regime gate: "
        + ("PASS" if regime_gate.passed else "FAIL")
    )
    console.print(
        f"regimes={regime_gate.observed_regimes} "
        f"spread={regime_gate.return_spread:.2%}"
    )
    if regime_gate.worst_regime is not None:
        console.print(
            f"worst_regime={regime_gate.worst_regime} "
            f"return={regime_gate.worst_return:.2%}"
        )
    if regime_gate.reasons:
        for reason in regime_gate.reasons:
            console.print(f"- {reason}")

    bootstrap = bootstrap_equity_curve(report.equity_curve)
    bootstrap_gate = evaluate_bootstrap_gate(bootstrap)
    console.print(
        "Bootstrap gate: "
        + ("PASS" if bootstrap_gate.passed else "FAIL")
    )
    console.print(
        f"p_positive={bootstrap.probability_positive:.1%} "
        f"p_loss={bootstrap.probability_loss:.1%} "
        f"lower_return={bootstrap.lower_return:.2%} "
        f"tail_drawdown={bootstrap.upper_max_drawdown:.2%}"
    )
    if bootstrap_gate.reasons:
        for reason in bootstrap_gate.reasons:
            console.print(f"- {reason}")

    sensitivity = run_parameter_sensitivity(backtester, df)
    sensitivity_gate = evaluate_sensitivity_gate(sensitivity)
    console.print(
        "Sensitivity gate: "
        + ("PASS" if sensitivity_gate.passed else "FAIL")
    )
    console.print(
        f"passing={sensitivity_gate.passing_scenarios}/"
        f"{sensitivity_gate.scenarios} "
        f"ratio={sensitivity_gate.pass_ratio:.0%} "
        f"worst_excess={sensitivity_gate.worst_excess_return:.2%} "
        f"worst_sharpe={sensitivity_gate.worst_sharpe:.2f} "
        f"worst_drawdown={sensitivity_gate.worst_drawdown:.2%}"
    )
    if sensitivity_gate.reasons:
        for reason in sensitivity_gate.reasons:
            console.print(f"- {reason}")

    cost_stress = run_cost_stress(backtester, df)
    cost_stress_gate = evaluate_cost_stress_gate(cost_stress)
    console.print(
        "Cost stress gate: "
        + ("PASS" if cost_stress_gate.passed else "FAIL")
    )
    console.print(
        f"passing={cost_stress_gate.passing_scenarios}/"
        f"{cost_stress_gate.scenarios} "
        f"ratio={cost_stress_gate.pass_ratio:.0%} "
        f"worst_excess={cost_stress_gate.worst_excess_return:.2%} "
        f"worst_sharpe={cost_stress_gate.worst_sharpe:.2f} "
        f"worst_drawdown={cost_stress_gate.worst_drawdown:.2%}"
    )
    if cost_stress_gate.reasons:
        for reason in cost_stress_gate.reasons:
            console.print(f"- {reason}")

    quantitative = evaluate_quantitative_qualification(
        benchmark=gate,
        regime=regime_gate,
        bootstrap=bootstrap_gate,
        sensitivity=sensitivity_gate,
        cost_stress=cost_stress_gate,
    )
    console.print(
        "Quantitative qualification: "
        + ("QUALIFIED" if quantitative.qualified else "REJECTED")
        + f" ({quantitative.passed_gates}/{quantitative.total_gates})"
    )
    if quantitative.reasons:
        for reason in quantitative.reasons:
            console.print(f"- {reason}")

    dataset = build_dataset_evidence(
        df,
        provider="yfinance",
        acquired_at_utc=datetime.now(UTC).isoformat(),
    )
    config_payload = {
        "risk": asdict(risk_config),
        "model": asdict(model_config),
        "walk_forward": asdict(wf_config),
    }
    config_hash = sha256(
        json.dumps(
            config_payload,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()
    artifact = build_quantitative_artifact(
        symbol=symbol,
        period=period,
        interval=interval,
        dataset=dataset,
        config_hash=config_hash,
        qualification=quantitative,
        benchmark=gate,
        regime=regime_gate,
        bootstrap=bootstrap_gate,
        sensitivity=sensitivity_gate,
        cost_stress=cost_stress_gate,
    )
    save_quantitative_artifact(artifact, qualification_artifact)
    console.print(f"Qualification artifact: {qualification_artifact}")

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


@app.command("expert-evolve")
def expert_evolve(
    symbol: str = typer.Option("GC=F", help="Yahoo Finance symbol"),
    period: str = typer.Option("5y", help="History period"),
    interval: str = typer.Option("1d", help="Bar interval"),
    parent_limit: int = typer.Option(3, min=1, max=10),
) -> None:
    df = load_history(symbol, period, interval)
    result = run_evolution_cycle(
        df,
        symbol=symbol,
        parent_limit=parent_limit,
    )

    table = Table(title=f"Expert evolution: {symbol}")
    table.add_column("Field")
    table.add_column("Value", justify="right")
    table.add_row("Generation", str(result.generation))
    table.add_row("Mutations evaluated", str(result.evaluated))
    table.add_row("Accepted", str(result.accepted))
    table.add_row("Portfolio replacements", str(result.replaced))
    table.add_row("Generation rollback", "YES" if result.rolled_back else "NO")
    console.print(table)


@app.command("generation-rollback")
def generation_rollback() -> None:
    pool = ExpertPoolStore()
    generations = GenerationStore()
    result = rollback_generation(pool, generations)

    table = Table(title="Generation rollback")
    table.add_column("Field")
    table.add_column("Value", justify="right")
    table.add_row("Restored generation", str(result.restored.generation))
    table.add_row("Portfolio score", f"{result.restored.portfolio_score:.4f}")
    table.add_row("Active experts", ", ".join(result.active_experts) or "-")
    console.print(table)


@app.command("multiasset-evolve")
def multiasset_evolve(
    symbols: str = typer.Option("GC=F,SI=F,CL=F", help="Comma-separated Yahoo symbols"),
    period: str = typer.Option("5y", help="History period"),
    interval: str = typer.Option("1d", help="Bar interval"),
    parent_limit: int = typer.Option(2, min=1, max=10),
    max_pair_correlation: float = typer.Option(0.85, min=0.0, max=1.0),
) -> None:
    names = [s.strip() for s in symbols.split(",") if s.strip()]
    if len(names) < 2:
        raise typer.BadParameter("Provide at least two symbols")

    markets = {name: load_history(name, period, interval) for name in names}
    result = run_multiasset_evolution_cycle(
        markets,
        parent_limit=parent_limit,
        max_pair_correlation=max_pair_correlation,
    )

    table = Table(title="Multi-asset expert evolution")
    table.add_column("Field")
    table.add_column("Value", justify="right")
    table.add_row("Generation", str(result.generation))
    table.add_row("Symbols", ", ".join(result.symbols))
    table.add_row("Evolved symbols", str(result.evolved_symbols))
    table.add_row("Portfolio score", f"{result.portfolio_score:.4f}")
    table.add_row("Diversified", "YES" if result.diversified else "NO")
    table.add_row("Max pair correlation", f"{result.max_pair_correlation:.3f}")
    table.add_row("Accepted", "YES" if result.accepted else "NO")
    table.add_row("Rolled back", "YES" if result.rolled_back else "NO")
    table.add_row("Reason", result.reason)
    console.print(table)


@app.command("global-allocation-check")
def global_allocation_check(
    symbols: str = typer.Option("GC=F,SI=F,CL=F", help="Comma-separated Yahoo symbols"),
    period: str = typer.Option("2y", help="History period"),
    interval: str = typer.Option("1d", help="Bar interval"),
) -> None:
    names = [s.strip() for s in symbols.split(",") if s.strip()]
    if len(names) < 2:
        raise typer.BadParameter("Provide at least two symbols")

    series = {}
    alpha = {}
    quality = {}
    for name in names:
        df = load_history(name, period, interval)
        ret = df["Close"].astype(float).pct_change().dropna()
        key = f"{name}|baseline|all"
        series[key] = ret
        alpha[key] = float(ret.tail(60).mean())
        quality[key] = 1.0

    frame = pd.DataFrame(series).dropna()
    report = allocate_global_capital(
        frame,
        expected_alpha=pd.Series(alpha),
        quality=pd.Series(quality),
        config=GlobalAllocatorConfig(
            max_turnover=2.0,
            max_cvar=0.20,
        ),
    )

    table = Table(title="Global capital allocator")
    table.add_column("Opportunity")
    table.add_column("Weight", justify="right")
    for key, weight in report.weights.items():
        table.add_row(str(key), f"{weight:.2%}")
    console.print(table)
    console.print(
        f"Approved={'YES' if report.approved else 'NO'} | "
        f"CVaR={report.cvar:.2%} | turnover={report.turnover:.2f} | "
        f"estimated_cost={report.estimated_cost:.4%}"
    )
    if report.reasons:
        console.print("; ".join(report.reasons))


@app.command("global-allocation-tune")
def global_allocation_tune(
    symbols: str = typer.Option("GC=F,SI=F,CL=F", help="Comma-separated Yahoo symbols"),
    period: str = typer.Option("5y", help="History period"),
    interval: str = typer.Option("1d", help="Bar interval"),
    trials: int = typer.Option(25, min=1, max=200),
    folds: int = typer.Option(3, min=2, max=6),
) -> None:
    names = [s.strip() for s in symbols.split(",") if s.strip()]
    if len(names) < 2:
        raise typer.BadParameter("Provide at least two symbols")

    series = {}
    for name in names:
        df = load_history(name, period, interval)
        series[f"{name}|baseline|all"] = df["Close"].astype(float).pct_change()

    frame = pd.DataFrame(series).dropna()
    result = tune_global_allocator(
        frame,
        trials=trials,
        folds=folds,
    )
    AllocatorConfigStore().save(result.best_config)

    table = Table(title="Global allocator tuning")
    table.add_column("Field")
    table.add_column("Value", justify="right")
    table.add_row("Best score", f"{result.best_score:.6f}")
    table.add_row("Trials", str(result.trials))
    table.add_row("CVaR alpha", f"{result.best_config.cvar_alpha:.4f}")
    table.add_row("Max CVaR", f"{result.best_config.max_cvar:.4f}")
    table.add_row("Max asset weight", f"{result.best_config.max_asset_weight:.4f}")
    table.add_row("Max expert weight", f"{result.best_config.max_expert_weight:.4f}")
    table.add_row("Max turnover", f"{result.best_config.max_turnover:.4f}")
    table.add_row("Target gross", f"{result.best_config.target_gross_exposure:.4f}")
    console.print(table)


@app.command("crisis-status")
def crisis_status() -> None:
    state = CrisisStateStore().load()
    limits = limits_for_state(state)

    table = Table(title="Crisis controller status")
    table.add_column("Field")
    table.add_column("Value", justify="right")
    table.add_row("Mode", state.mode)
    table.add_row("Recovery streak", str(state.recovery_streak))
    table.add_row("Exposure scale", f"{limits.exposure_scale:.2f}")
    table.add_row("Max active experts", str(limits.max_active_experts))
    table.add_row("Asset limit fraction", f"{limits.asset_limit_fraction:.2f}")
    table.add_row(
        "New promotions",
        "ENABLED" if limits.allow_new_promotions else "FROZEN",
    )
    console.print(table)


@app.command("risk-governor-status")
def risk_governor_status() -> None:
    state = GovernorStateStore().load()

    table = Table(title="Risk governor status")
    table.add_column("Field")
    table.add_column("Value", justify="right")
    table.add_row("Verdict", state.verdict)
    table.add_row("Reason", state.reason)
    table.add_row("Consecutive halts", str(state.consecutive_halts))
    console.print(table)


@app.command("system-status")
def system_status() -> None:
    status = read_control_plane()

    table = Table(title="AI Trading control plane")
    table.add_column("Field")
    table.add_column("Value", justify="right")
    table.add_row("Governor", status.governor_verdict)
    table.add_row("Governor reason", status.governor_reason)
    table.add_row("Crisis mode", status.crisis_mode)
    table.add_row("Recovery streak", str(status.recovery_streak))
    table.add_row(
        "Promotions",
        "ENABLED" if status.promotions_allowed else "FROZEN",
    )
    table.add_row(
        "Scheduler",
        "RUN" if status.scheduler_should_run else "HALT",
    )
    console.print(table)


@app.command("create-readiness-release")
def create_readiness_release_command(
    symbols: str = typer.Option("GC=F,SI=F,CL=F"),
    period: str = typer.Option("2y"),
    interval: str = typer.Option("1d"),
    qualification_path: str = typer.Option("artifacts/soak/qualification.json"),
    lifecycle_path: str = typer.Option("artifacts/model_lifecycle.jsonl"),
    resilience_path: str = typer.Option("artifacts/resilience_state.json"),
    governor_path: str = typer.Option("artifacts/risk_governor_state.json"),
    readiness_history_path: str = typer.Option("artifacts/readiness_history.jsonl"),
    release_path: str = typer.Option("artifacts/readiness_release.json"),
    revocations_path: str = typer.Option("artifacts/readiness_revocations.jsonl"),
    quantitative_artifact_path: str = typer.Option(
        "artifacts/quantitative_qualification.json"
    ),
    signing_key_env: str = typer.Option("AI_TRADING_RELEASE_SIGNING_KEY"),
    verify_reproducibility: bool = typer.Option(
        True, "--verify-reproducibility/--no-verify-reproducibility"
    ),
) -> None:
    names = tuple(s.strip() for s in symbols.split(",") if s.strip())
    if not names:
        raise typer.BadParameter("Provide at least one symbol")

    qualification = QualificationStore(qualification_path).load()
    if qualification is None:
        console.print("Qualification record missing")
        raise typer.Exit(code=2)

    resilience = ResilienceStateStore(resilience_path).load()
    governor = GovernorStateStore(governor_path).load()
    lifecycle = LifecycleEventLog(lifecycle_path)
    reliability = evaluate_reliability(lifecycle, resilience)
    readiness_store = ReadinessHistoryStore(readiness_history_path)
    history = readiness_store.list()
    chain = readiness_store.verify_chain()
    if not history:
        console.print("Readiness history missing")
        raise typer.Exit(code=2)

    composite = history[-1].result
    trend = evaluate_readiness_trend(history)

    readiness = evaluate_deployment_readiness(
        qualification,
        reliability=reliability,
        resilience=resilience,
        governor=governor,
        symbols=names,
        period=period,
        interval=interval,
        composite=composite,
        trend=trend,
        readiness_chain=chain,
        policy=DeploymentReadinessPolicy(require_release_manifest=False),
    )
    blocking = tuple(
        reason
        for reason in readiness.reasons
        if reason != "readiness release manifest missing"
    )
    if blocking:
        console.print("Cannot create readiness release:")
        for reason in blocking:
            console.print(f"- {reason}")
        raise typer.Exit(code=2)

    quantitative_artifact = load_quantitative_artifact(
        quantitative_artifact_path
    )
    if quantitative_artifact is None:
        console.print("Quantitative qualification artifact missing or invalid")
        raise typer.Exit(code=2)
    if quantitative_artifact.verdict != "QUALIFIED":
        console.print("Quantitative qualification is not QUALIFIED")
        raise typer.Exit(code=2)

    if verify_reproducibility:
        benchmark_data = load_history(
            quantitative_artifact.symbol,
            quantitative_artifact.period,
            quantitative_artifact.interval,
        )
        reproducibility = verify_quantitative_reproducibility(
            quantitative_artifact,
            benchmark_data,
            provider=quantitative_artifact.dataset.provider,
        )
        if not reproducibility.valid:
            console.print("Quantitative evidence is not reproducible:")
            for reason in reproducibility.reasons:
                console.print(f"- {reason}")
            raise typer.Exit(code=2)

    signing_key = os.getenv(signing_key_env)
    if not signing_key:
        console.print(f"Missing signing key environment variable: {signing_key_env}")
        raise typer.Exit(code=2)

    release = create_readiness_release(
        composite=composite,
        chain_head=history[-1].record_hash,
        chain=chain,
        qualification=qualification,
        governor=governor,
        resilience=resilience,
        trend=trend,
        signing_key=signing_key,
        quantitative_evidence_hash=quantitative_artifact.evidence_hash,
    )
    ReadinessReleaseStore(release_path).save(release)
    console.print(f"Readiness release created: {release.release_hash}")


@app.command("revoke-readiness-release")
def revoke_readiness_release(
    reason: str = typer.Option(...),
    release_path: str = typer.Option("artifacts/readiness_release.json"),
    revocations_path: str = typer.Option("artifacts/readiness_revocations.jsonl"),
) -> None:
    release = ReadinessReleaseStore(release_path).load()
    if release is None:
        console.print("Readiness release missing")
        raise typer.Exit(code=2)

    record = ReadinessRevocationStore(revocations_path).revoke(
        release.release_hash,
        reason=reason,
    )
    console.print(
        f"Revoked readiness release {record.release_hash}: {record.reason}"
    )


@app.command("deployment-readiness")
def deployment_readiness(
    symbols: str = typer.Option("GC=F,SI=F,CL=F"),
    period: str = typer.Option("2y"),
    interval: str = typer.Option("1d"),
    qualification_path: str = typer.Option("artifacts/soak/qualification.json"),
    lifecycle_path: str = typer.Option("artifacts/model_lifecycle.jsonl"),
    resilience_path: str = typer.Option("artifacts/resilience_state.json"),
    governor_path: str = typer.Option("artifacts/risk_governor_state.json"),
    readiness_history_path: str = typer.Option("artifacts/readiness_history.jsonl"),
    release_path: str = typer.Option("artifacts/readiness_release.json"),
    revocations_path: str = typer.Option("artifacts/readiness_revocations.jsonl"),
    quantitative_artifact_path: str = typer.Option(
        "artifacts/quantitative_qualification.json"
    ),
    signing_key_env: str = typer.Option("AI_TRADING_RELEASE_SIGNING_KEY"),
) -> None:
    names = tuple(s.strip() for s in symbols.split(",") if s.strip())
    if not names:
        raise typer.BadParameter("Provide at least one symbol")

    qualification = QualificationStore(qualification_path).load()
    resilience_store = ResilienceStateStore(resilience_path)
    resilience = resilience_store.load()
    lifecycle = LifecycleEventLog(lifecycle_path)
    reliability = evaluate_reliability(lifecycle, resilience)
    governor = GovernorStateStore(governor_path).load()
    readiness_store = ReadinessHistoryStore(readiness_history_path)
    readiness_history = readiness_store.list()
    readiness_chain = readiness_store.verify_chain()
    composite = readiness_history[-1].result if readiness_history else None
    trend = evaluate_readiness_trend(readiness_history)
    release_store = ReadinessReleaseStore(release_path)
    release = release_store.load()
    revocation_store = ReadinessRevocationStore(revocations_path)
    release_verification = None
    signing_key = os.getenv(signing_key_env)
    quantitative_artifact = load_quantitative_artifact(
        quantitative_artifact_path
    )
    quantitative_evidence_hash = (
        quantitative_artifact.evidence_hash
        if quantitative_artifact is not None
        and quantitative_artifact.verdict == "QUALIFIED"
        else ""
    )
    quantitative_reproducible = False
    if quantitative_artifact is not None and quantitative_artifact.verdict == "QUALIFIED":
        benchmark_data = load_history(
            quantitative_artifact.symbol,
            quantitative_artifact.period,
            quantitative_artifact.interval,
        )
        quantitative_reproducible = verify_quantitative_reproducibility(
            quantitative_artifact,
            benchmark_data,
            provider=quantitative_artifact.dataset.provider,
        ).valid
        if not quantitative_reproducible:
            quantitative_evidence_hash = ""
    if release is not None and composite is not None and qualification is not None:
        release_verification = verify_readiness_release(
            release,
            composite=composite,
            chain_head=readiness_history[-1].record_hash,
            chain=readiness_chain,
            qualification=qualification,
            governor=governor,
            resilience=resilience,
            trend=trend,
            signing_key=signing_key,
            quantitative_evidence_hash=quantitative_evidence_hash,
        )

    readiness = evaluate_deployment_readiness(
        qualification,
        reliability=reliability,
        resilience=resilience,
        governor=governor,
        symbols=names,
        period=period,
        interval=interval,
        composite=composite,
        trend=trend,
        readiness_chain=readiness_chain,
        release_verification=release_verification,
        release_hash=(release.release_hash if release is not None else None),
        revocation_store=revocation_store,
        quantitative_reproducible=quantitative_reproducible,
    )

    table = Table(title="Paper-to-live deployment readiness")
    table.add_column("Field")
    table.add_column("Value", justify="right")
    table.add_row("Decision", "READY" if readiness.allowed else "BLOCKED")
    table.add_row("Reliability score", f"{reliability.reliability_score:.2f}")
    table.add_row("Observation", f"{reliability.observation_seconds / 86400.0:.2f} days")
    table.add_row("NORMAL ratio", f"{reliability.normal_ratio:.2%}")
    table.add_row("HALT ratio", f"{reliability.halt_ratio:.2%}")
    table.add_row(
        "MTTR",
        "-" if reliability.mttr_seconds is None else f"{reliability.mttr_seconds:.1f}s",
    )
    table.add_row(
        "MTBF",
        "-" if reliability.mtbf_seconds is None else f"{reliability.mtbf_seconds:.1f}s",
    )
    table.add_row("Resilience", resilience.mode)
    table.add_row("Instability", resilience.instability_status)
    table.add_row("Governor", governor.verdict)
    table.add_row(
        "Composite readiness",
        "-" if composite is None else f"{composite.score:.2f}",
    )
    table.add_row(
        "Readiness formula",
        "-" if composite is None else composite.version,
    )
    table.add_row(
        "Evidence hash",
        "-" if composite is None else composite.evidence_hash[:16],
    )
    table.add_row("Readiness trend", trend.status)
    table.add_row("Trend observations", str(trend.observations))
    table.add_row("Trend score change", f"{trend.score_change:+.2f}")
    table.add_row(
        "Readiness chain",
        "VALID" if readiness_chain.valid else "INVALID",
    )
    table.add_row("Readiness records", str(readiness_chain.records))
    table.add_row(
        "Readiness release",
        "VALID"
        if release_verification is not None and release_verification.valid
        else "MISSING/INVALID",
    )
    table.add_row(
        "Quantitative reproducibility",
        "VALID" if quantitative_reproducible else "MISSING/INVALID",
    )
    console.print(table)

    if readiness.reasons:
        console.print("Blocking reasons:")
        for reason in readiness.reasons:
            console.print(f"- {reason}")

    if not readiness.allowed:
        raise typer.Exit(code=2)


@app.command("multiasset-loop")
def multiasset_loop(
    symbols: str = typer.Option("GC=F,SI=F,CL=F", help="Comma-separated Yahoo symbols"),
    period: str = typer.Option("1y", help="History period"),
    interval: str = typer.Option("1d", help="Bar interval"),
    poll_seconds: float = typer.Option(60.0, min=0.0),
    max_iterations: int = typer.Option(1, min=1, max=10000),
) -> None:
    names = [s.strip() for s in symbols.split(",") if s.strip()]
    if len(names) < 2:
        raise typer.BadParameter("Provide at least two symbols")

    def loader() -> dict[str, pd.DataFrame]:
        return {
            name: load_history(name, period, interval)
            for name in names
        }

    scheduler = MultiAssetPaperScheduler(
        runtime=MultiAssetPaperRuntime(),
        data_loader=loader,
        config=MultiAssetSchedulerConfig(
            poll_seconds=poll_seconds,
            max_iterations=max_iterations,
        ),
    )
    results = scheduler.run()

    table = Table(title="Multi-asset paper loop")
    table.add_column("Field")
    table.add_column("Value", justify="right")
    table.add_row("Iterations", str(len(results)))
    if results:
        last = results[-1]
        table.add_row("Last equity", f"{last.equity:,.2f}")
        table.add_row("Last cash", f"{last.cash:,.2f}")
        table.add_row("Risk approved", "YES" if last.risk_approved else "NO")
    console.print(table)


@app.command("watchdog-status")
def watchdog_status() -> None:
    heartbeat_store = HeartbeatStore("artifacts/multiasset_heartbeat.json")
    heartbeat = heartbeat_store.load()
    audit_path = "artifacts/multiasset_audit.jsonl"
    audit = verify_jsonl_audit(audit_path)
    chain = verify_audit_chain(audit_path)
    snapshot = AtomicSnapshotStore().latest_valid()

    table = Table(title="Paper watchdog status")
    table.add_column("Field")
    table.add_column("Value", justify="right")
    table.add_row(
        "Heartbeat",
        "MISSING" if heartbeat is None else heartbeat.status,
    )
    table.add_row(
        "Heartbeat stale",
        "YES" if heartbeat_is_stale(heartbeat) else "NO",
    )
    table.add_row("Audit JSON valid", "YES" if audit.valid else "NO")
    table.add_row("Audit chain valid", "YES" if chain.valid else "NO")
    table.add_row("Audit legacy lines", str(chain.legacy_lines))
    table.add_row("Audit lines", str(audit.lines))
    table.add_row(
        "Last valid snapshot",
        "-" if snapshot is None else snapshot.name,
    )
    console.print(table)


@app.command("watchdog-enforce")
def watchdog_enforce(
    max_heartbeat_age_seconds: float = typer.Option(180.0, min=1.0),
) -> None:
    result = enforce_watchdog(
        heartbeat_store=HeartbeatStore("artifacts/multiasset_heartbeat.json"),
        audit_path="artifacts/multiasset_audit.jsonl",
        governor_store=GovernorStateStore(),
        policy=WatchdogPolicy(
            max_heartbeat_age_seconds=max_heartbeat_age_seconds,
        ),
    )

    table = Table(title="Watchdog enforcement")
    table.add_column("Field")
    table.add_column("Value", justify="right")
    table.add_row("Healthy", "YES" if result.healthy else "NO")
    table.add_row("Halted", "YES" if result.halted else "NO")
    table.add_row(
        "Reasons",
        "-" if not result.reasons else "; ".join(result.reasons),
    )
    console.print(table)


@app.command("maintenance")
def maintenance(
    enabled: bool = typer.Option(..., help="Enable or disable maintenance mode"),
    reason: str = typer.Option("", help="Maintenance reason"),
) -> None:
    store = MaintenanceStore()
    store.save(MaintenanceState(enabled=enabled, reason=reason))
    console.print(
        f"Maintenance={'ON' if enabled else 'OFF'}"
        + (f" | {reason}" if reason else "")
    )


@app.command("supervisor-status")
def supervisor_status() -> None:
    lease = SupervisorLeaseStore().load()
    maintenance_state = MaintenanceStore().load()

    table = Table(title="Paper supervisor status")
    table.add_column("Field")
    table.add_column("Value", justify="right")
    table.add_row(
        "Lease PID",
        "-" if lease is None else str(lease.owner_pid),
    )
    table.add_row(
        "Maintenance",
        "ON" if maintenance_state.enabled else "OFF",
    )
    table.add_row(
        "Maintenance reason",
        maintenance_state.reason or "-",
    )
    console.print(table)


@app.command("metrics")
def metrics() -> None:
    console.print(prometheus_text(collect_metrics()), markup=False)


@app.command("health-serve")
def health_serve(
    host: str = typer.Option("127.0.0.1"),
    port: int = typer.Option(8765, min=1, max=65535),
) -> None:
    server = HealthServer(host=host, port=port)
    server.start()
    console.print(f"Health endpoint listening on http://{host}:{port}/health")
    try:
        import time

        while True:
            time.sleep(3600)
    except KeyboardInterrupt:
        server.stop()


@app.command("supervisor-run")
def supervisor_run(
    symbols: str = typer.Option("GC=F,SI=F,CL=F"),
    period: str = typer.Option("1y"),
    interval: str = typer.Option("1d"),
    poll_seconds: float = typer.Option(60.0, min=0.0),
    max_iterations: int = typer.Option(1000000, min=1),
    max_restarts: int = typer.Option(10, min=0, max=100),
    require_qualification: bool = typer.Option(False),
    qualification_path: str = typer.Option("artifacts/soak/qualification.json"),
) -> None:
    names = [s.strip() for s in symbols.split(",") if s.strip()]
    if len(names) < 2:
        raise typer.BadParameter("Provide at least two symbols")

    command = [
        sys.executable,
        "-m",
        "ai_trading.cli",
        "multiasset-loop",
        "--symbols",
        ",".join(names),
        "--period",
        period,
        "--interval",
        interval,
        "--poll-seconds",
        str(poll_seconds),
        "--max-iterations",
        str(max_iterations),
    ]

    runtime = MultiAssetPaperRuntime()
    supervisor = PaperSupervisor(
        command=command,
        state_files=[
            runtime.state_store.path,
            runtime.crisis_state_store.path,
            runtime.governor_state_store.path,
            runtime.allocation_state_store.path,
            runtime.allocator_config_store.path,
            runtime.drift_retrain_store.path,
        ],
        audit_path=runtime.audit.path,
        config=SupervisorConfig(
            max_restarts=max_restarts,
            require_qualification=require_qualification,
            qualification_symbols=tuple(names),
            qualification_period=period,
            qualification_interval=interval,
        ),
        qualification_store=QualificationStore(qualification_path),
    )
    result = supervisor.run()

    table = Table(title="Paper supervisor result")
    table.add_column("Field")
    table.add_column("Value", justify="right")
    table.add_row("Restarts", str(result.restarts))
    table.add_row(
        "Maintenance stop",
        "YES" if result.stopped_for_maintenance else "NO",
    )
    table.add_row(
        "Crash loop",
        "YES" if result.crash_loop_detected else "NO",
    )
    table.add_row(
        "Final exit code",
        "-" if result.final_exit_code is None else str(result.final_exit_code),
    )
    console.print(table)


@app.command("paper-soak")
def paper_soak(
    symbols: str = typer.Option("GC=F,SI=F,CL=F"),
    period: str = typer.Option("2y"),
    interval: str = typer.Option("1d"),
    max_cycles: int = typer.Option(100, min=1, max=5000),
    chaos_symbol: str = typer.Option(""),
    chaos_step: int = typer.Option(-1),
    chaos_name: str = typer.Option("ohlc_violation"),
    workspace: str = typer.Option("artifacts/soak"),
) -> None:
    names = [s.strip() for s in symbols.split(",") if s.strip()]
    if len(names) < 2:
        raise typer.BadParameter("Provide at least two symbols")

    markets = {
        name: load_history(name, period, interval)
        for name in names
    }

    chaos = ()
    if chaos_step >= 0:
        target = chaos_symbol.strip() or names[0]
        chaos = (
            ChaosScenario(
                name=chaos_name,
                step=chaos_step,
                symbol=target,
            ),
        )

    result = run_multiasset_soak(
        isolated_multiasset_runtime(workspace),
        markets,
        max_cycles=max_cycles,
        chaos=chaos,
    )

    table = Table(title="Multi-asset paper soak")
    table.add_column("Field")
    table.add_column("Value", justify="right")
    table.add_row("Cycles", str(result.cycles))
    table.add_row("Successes", str(result.successes))
    table.add_row("Failures", str(result.failures))
    table.add_row(
        "Final equity",
        "-" if result.final_equity is None else f"{result.final_equity:,.2f}",
    )
    table.add_row(
        "Minimum equity",
        "-" if result.min_equity is None else f"{result.min_equity:,.2f}",
    )
    table.add_row("Max drawdown", f"{result.max_drawdown:.2%}")
    qualification = evaluate_soak_qualification(result)
    QualificationStore(Path(workspace) / "qualification.json").save(
        result,
        qualification,
        symbols=tuple(names),
        period=period,
        interval=interval,
    )
    table.add_row("Governor", result.governor_verdict)
    table.add_row("Crisis mode", result.crisis_mode)
    table.add_row(
        "Qualification",
        "PASS" if qualification.passed else "FAIL",
    )
    table.add_row(
        "Success ratio",
        f"{qualification.success_ratio:.2%}",
    )
    console.print(table)

    if qualification.reasons:
        console.print("Qualification reasons:")
        for reason in qualification.reasons:
            console.print(reason)

    if result.errors:
        console.print("Recent errors:")
        for error in result.errors[-10:]:
            console.print(error)


@app.command("paper-qualification-suite")
def paper_qualification_suite(
    symbols: str = typer.Option("GC=F,SI=F,CL=F"),
    period: str = typer.Option("2y"),
    interval: str = typer.Option("1d"),
    max_cycles: int = typer.Option(100, min=10, max=5000),
    workspace: str = typer.Option("artifacts/qualification_suite"),
) -> None:
    names = [s.strip() for s in symbols.split(",") if s.strip()]
    if len(names) < 2:
        raise typer.BadParameter("Provide at least two symbols")

    markets = {
        name: load_history(name, period, interval)
        for name in names
    }
    result = run_qualification_suite(
        markets,
        workspace_root=workspace,
        max_cycles=max_cycles,
    )

    table = Table(title="Paper qualification suite")
    table.add_column("Case")
    table.add_column("Successes", justify="right")
    table.add_column("Failures", justify="right")
    table.add_column("Governor")
    table.add_column("Baseline PASS")
    table.add_column("Safe fault")

    for case in result.cases:
        table.add_row(
            case.name,
            str(case.soak.successes),
            str(case.soak.failures),
            case.soak.governor_verdict,
            "YES" if case.qualification.passed else "NO",
            "YES" if case.expected_safe_failure else "NO",
        )

    console.print(table)
    console.print(f"Suite={'PASS' if result.passed else 'FAIL'}")
    if result.reasons:
        for reason in result.reasons:
            console.print(reason)


if __name__ == "__main__":
    app()

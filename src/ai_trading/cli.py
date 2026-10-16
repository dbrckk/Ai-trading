import json
import os
import sys
from pathlib import Path
from typing import Optional

import rich
import typer
from rich.console import Console
from rich.table import Table

from ai_trading import __version__
from ai_trading.allocator_config_store import AllocatorConfigStore
from ai_trading.allocator_tuning import allocator_tuning_command
from ai_trading.audit_chain import AuditChain
from ai_trading.audit_integrity import audit_integrity_command
from ai_trading.backtest import backtest_command
from ai_trading.bootstrap_gate import bootstrap_gate_command
from ai_trading.bootstrap_robustness import bootstrap_robustness_command
from ai_trading.champions import champions_command
from ai_trading.chaos import chaos_command
from ai_trading.command_app import app
from ai_trading.continuous import continuous_command
from ai_trading.control_plane import control_plane_command
from ai_trading.cost_stress import cost_stress_command
from ai_trading.cost_stress_gate import cost_stress_gate_command
from ai_trading.crisis_controller import crisis_controller_command
from ai_trading.crisis_state_store import CrisisStateStore
from ai_trading.dataset_evidence import dataset_evidence_command
from ai_trading.deployment_readiness import deployment_readiness_command
from ai_trading.drift import drift_command
from ai_trading.engine import engine_command
from ai_trading.evolution_manager import evolution_manager_command
from ai_trading.experiments import experiments_command
from ai_trading.expert_factory import expert_factory_command
from ai_trading.expert_pool import expert_pool_command
from ai_trading.expert_pool_manager import expert_pool_manager_command
from ai_trading.expert_sandbox import expert_sandbox_command
from ai_trading.generation_rollback import generation_rollback_command
from ai_trading.generations import generations_command
from ai_trading.global_allocator import global_allocator_command
from ai_trading.governor_state_store import GovernorStateStore
from ai_trading.guardrails import guardrails_command
from ai_trading.health_server import health_server_command
from ai_trading.lifecycle_log import lifecycle_log_command
from ai_trading.maintenance import maintenance_command
from ai_trading.metrics import metrics_command
from ai_trading.multiasset_backtest import multiasset_backtest_command
from ai_trading.multiasset_evolution import multiasset_evolution_command
from ai_trading.multiasset_runtime import multiasset_runtime_command
from ai_trading.multiasset_scheduler import multiasset_scheduler_command
from ai_trading.orchestrator import orchestrator_command
from ai_trading.parameter_sensitivity import parameter_sensitivity_command
from ai_trading.performance import performance_command
from ai_trading.portfolio import portfolio_command
from ai_trading.portfolio_risk import portfolio_risk_command
from ai_trading.promotion import promotion_command
from ai_trading.qualification_store import qualification_store_command
from ai_trading.qualification_suite import qualification_suite_command
from ai_trading.quantitative_artifact import quantitative_artifact_command
from ai_trading.quantitative_qualification import quantitative_qualification_command
from ai_trading.readiness import readiness_command
from ai_trading.readiness_release import readiness_release_command
from ai_trading.readiness_revocation import readiness_revocation_command
from ai_trading.readiness_score import readiness_score_command
from ai_trading.readiness_trend import readiness_trend_command
from ai_trading.regime_gate import regime_gate_command
from ai_trading.regime_validation import regime_validation_command
from ai_trading.reliability import reliability_command
from ai_trading.reproducibility import reproducibility_command
from ai_trading.resilience import resilience_command
from ai_trading.robustness import robustness_command
from ai_trading.runtime import runtime_command
from ai_trading.runtime_factory import runtime_factory_command
from ai_trading.scheduler import scheduler_command
from ai_trading.sensitivity_gate import sensitivity_gate_command
from ai_trading.soak import soak_command
from ai_trading.soak_gate import soak_gate_command
from ai_trading.state_snapshot import state_snapshot_command
from ai_trading.supervisor import supervisor_command
from ai_trading.supervisor_lease import supervisor_lease_command
from ai_trading.tuning import tuning_command
from ai_trading.watchdog import watchdog_command
from ai_trading.watchdog_enforcer import watchdog_enforcer_command

# New import for TradingAgents
try:
    from tradingagents import __version__ as tradingagents_version
    TRADING_AGENTS_AVAILABLE = True
except ImportError:
    TRADING_AGENTS_AVAILABLE = False


@app.command()
def version():
    """Show version and exit."""
    typer.echo(f"ai-trading version: {__version__}")
    if TRADING_AGENTS_AVAILABLE:
        typer.echo(f"TradingAgents version: {tradingagents_version}")
    else:
        typer.echo("TradingAgents is not installed.", err=True)


@app.command()
def trade_agents_demo():
    """Demonstrate TradingAgents integration."""
    if not TRADING_AGENTS_AVAILABLE:
        typer.echo("TradingAgents is not installed. Please install it to use this command.", err=True)
        raise typer.Exit(code=1)
    
    # Example usage: we assume TradingAgents has a simple function to get version or run a basic agent
    # Since we don't know the exact API, we demonstrate by checking the version and printing a message.
    typer.echo(f"TradingAgents version: {tradingagents_version}")
    typer.echo("TradingAgents is successfully integrated and accessible.")
    # If there is a simple agent we can run without external dependencies, we would do it here.
    # For example, if TradingAgents has a dummy agent:
    #   from tradingagents.agents import DummyAgent
    #   agent = DummyAgent()
    #   result = agent.run()
    #   typer.echo(f"Dummy agent result: {result}")
    # But without knowing the API, we stick to version check.


if __name__ == "__main__":
    app()

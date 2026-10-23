This file is a merged representation of a subset of the codebase, containing specifically included files and files not matching ignore patterns, combined into a single document by Repomix.
The content has been processed where content has been compressed (code blocks are separated by ⋮---- delimiter).

# File Summary

## Purpose
This file contains a packed representation of a subset of the repository's contents that is considered the most important context.
It is designed to be easily consumable by AI systems for analysis, code review,
or other automated processes.

## File Format
The content is organized as follows:
1. This summary section
2. Repository information
3. Directory structure
4. Repository files (if enabled)
5. Multiple file entries, each consisting of:
  a. A header with the file path (## File: path/to/file)
  b. The full contents of the file in a code block

## Usage Guidelines
- This file should be treated as read-only. Any changes should be made to the
  original repository files, not this packed version.
- When processing this file, use the file path to distinguish
  between different files in the repository.
- Be aware that this file may contain sensitive information. Handle it with
  the same level of security as you would the original repository.

## Notes
- Some files may have been excluded based on .gitignore rules and Repomix's configuration
- Binary files are not included in this packed representation. Please refer to the Repository Structure section for a complete list of file paths, including binary files
- Only files matching these patterns are included: **/*.{py,js,mjs,cjs,ts,tsx,jsx,java,kt,kts,gd,groovy,gradle,toml,json,yaml,yml,sql,sh}
- Files matching these patterns are excluded: .ai/**, **/node_modules/**, **/.gradle/**, **/build/**, **/dist/**, **/.venv/**, **/__pycache__/**, **/.pytest_cache/**, **/.git/**, **/coverage/**, **/*.lock, **/*.min.js, **/*.map, assets/**, art/**, art_sources/**, marketing/**, colab/**, kaggle/**, discovery-cache.json, health-snapshot.json, history.json
- Files matching patterns in .gitignore are excluded
- Files matching default ignore patterns are excluded
- Content has been compressed - code blocks are separated by ⋮---- delimiter
- Files are sorted by Git change count (files with more changes are at the bottom)

# Directory Structure
```
test_active_model.py
test_allocation_state.py
test_allocator_config_store.py
test_allocator_tuning.py
test_alpha_allocation.py
test_alpha_attribution.py
test_asset_classes.py
test_audit_chain_legacy.py
test_audit_chain.py
test_audit_integrity.py
test_audit.py
test_backtest_ensemble.py
test_backtest.py
test_benchmark_gate.py
test_bootstrap_gate.py
test_bootstrap_robustness.py
test_broker.py
test_burnin.py
test_calibration_routing.py
test_champion_probation.py
test_champions.py
test_chaos.py
test_checkpoint_verification.py
test_cli_self_test.py
test_cloudflare_scheduler_deploy_workflow.py
test_compute_budget.py
test_confidence_calibration.py
test_config_validation.py
test_control_plane.py
test_cost_stress_gate.py
test_cost_stress.py
test_crisis_controller.py
test_crisis_gate.py
test_cumulative_performance_persistence.py
test_dashboard_engine_status.py
test_dashboard_health.py
test_dashboard_overview.py
test_dashboard_persistence.py
test_dashboard.py
test_data_quality.py
test_data.py
test_dataset_evidence.py
test_deployment_readiness.py
test_distribution_drift.py
test_drift_retrain_store.py
test_drift.py
test_durable_burnin_persistence.py
test_economic_meta_store.py
test_economic_meta.py
test_ensemble.py
test_evolution_manager.py
test_evolution.py
test_execution_costs.py
test_expert_diversity.py
test_expert_factory.py
test_expert_horizon.py
test_expert_lifecycle.py
test_expert_pool_manager.py
test_expert_pool.py
test_expert_sandbox.py
test_expert_uncertainty.py
test_features.py
test_file_persistence.py
test_generation_progress.py
test_generation_rollback.py
test_generations.py
test_global_allocator.py
test_global_selection.py
test_governor_state_store.py
test_guardrails.py
test_health_server.py
test_hosted_persistence.py
test_hosted_runtime.py
test_lifecycle_log.py
test_maintenance.py
test_marginal_alpha.py
test_market_freshness.py
test_meta_router.py
test_meta_store.py
test_metrics.py
test_model_blend.py
test_model_codec.py
test_model_quality.py
test_model_quarantine.py
test_mtf_parameter_benchmark.py
test_mtf_shadow_challenger.py
test_mtf_shadow_config.py
test_mtf_shadow_quality.py
test_multi_market.py
test_multi_period_promotion.py
test_multi_timeframe_features.py
test_multiasset_backtest.py
test_multiasset_checkpoint_consistency.py
test_multiasset_checkpoint_manifest_binding.py
test_multiasset_checkpoint_orphan_corruption.py
test_multiasset_checkpoint.py
test_multiasset_evolution.py
test_multiasset_market_context.py
test_multiasset_runtime.py
test_multiasset_scheduler.py
test_multiasset_state.py
test_online.py
test_orchestrator_trigger.py
test_paper_cycle_cli.py
test_paper_cycle_materialized_fresh.py
test_paper_cycle_postgres.py
test_paper_cycle_service.py
test_paper_cycle_workflow.py
test_paper_cycle.py
test_paper_execution.py
test_performance_metrics.py
test_performance.py
test_persistence_contract.py
test_persistence_factory.py
test_persistence.py
test_pnl_attribution.py
test_portfolio_intelligence.py
test_portfolio_risk.py
test_portfolio_selection.py
test_portfolio.py
test_postgres_persistence.py
test_process_watch.py
test_promotion_guard.py
test_promotion.py
test_purged_cv.py
test_qualification_guard.py
test_qualification_store.py
test_qualification_suite.py
test_quality_store.py
test_quantitative_artifact.py
test_quantitative_qualification.py
test_readiness_evidence.py
test_readiness_handshake.py
test_readiness_release.py
test_readiness_revocation.py
test_readiness_score.py
test_readiness_trend.py
test_readiness.py
test_realized_pnl_accounting.py
test_recovery_health.py
test_recovery.py
test_regime_gate.py
test_regime_validation.py
test_regime.py
test_reliability.py
test_replay.py
test_reproducibility.py
test_research_config_validation.py
test_resilience_stability.py
test_resilience.py
test_risk_governor.py
test_risk_parity.py
test_risk.py
test_robustness.py
test_rollback_model.py
test_runtime_factory.py
test_runtime_lock.py
test_runtime_persistence.py
test_runtime_state.py
test_runtime_status.py
test_runtime_targeted_step.py
test_runtime.py
test_scheduler_endpoint.py
test_scheduler_governor.py
test_scheduler_iteration_callback.py
test_scheduler.py
test_sensitivity_gate.py
test_session_integrity.py
test_shadow_challenger.py
test_shadow_promotion_gate.py
test_shadow_quality.py
test_smoke_e2e.py
test_snapshot_retention.py
test_soak_gate_drawdown.py
test_soak_gate.py
test_specialist_experts.py
test_startup_check.py
test_state_hash.py
test_state_snapshot.py
test_stress_engine.py
test_supervisor_clean_exit.py
test_supervisor_crash_loop.py
test_supervisor_lease.py
test_supervisor_qualification.py
test_supervisor_state.py
test_supervisor.py
test_temporal_cv.py
test_tuning.py
test_watchdog_enforcer.py
test_watchdog.py
test_worker_monitor.py
```

# Files

## File: test_active_model.py
```python
def test_active_model_pointer_round_trip(tmp_path: Path) -> None
⋮----
store = ModelStore(tmp_path / "models")
```

## File: test_allocation_state.py
```python
def test_allocation_state_round_trip(tmp_path: Path) -> None
⋮----
store = AllocationStateStore(tmp_path / "allocation.json")
weights = pd.Series({"A|x|r": 0.4, "B|y|r": 0.6})
⋮----
loaded = store.load()
```

## File: test_allocator_config_store.py
```python
def test_allocator_config_store_round_trip(tmp_path: Path) -> None
⋮----
store = AllocatorConfigStore(tmp_path / "allocator.json")
config = GlobalAllocatorConfig(
```

## File: test_allocator_tuning.py
```python
def test_allocator_tuning_returns_valid_config() -> None
⋮----
rng = np.random.default_rng(21)
columns = [
returns = pd.DataFrame(
result = tune_global_allocator(
```

## File: test_alpha_allocation.py
```python
def test_alpha_risk_allocation_prefers_stronger_alpha_per_risk() -> None
⋮----
weights = alpha_risk_weights(
```

## File: test_alpha_attribution.py
```python
def test_alpha_attribution_tracks_model_and_regime() -> None
⋮----
item = build_alpha_contribution(
```

## File: test_asset_classes.py
```python
def test_common_symbols_are_classified() -> None
⋮----
def test_energy_is_disabled_in_capital_preservation_by_default() -> None
```

## File: test_audit_chain_legacy.py
```python
def test_legacy_prefix_can_transition_to_chained_audit(tmp_path: Path) -> None
⋮----
path = tmp_path / "audit.jsonl"
⋮----
report = verify_audit_chain(path)
```

## File: test_audit_chain.py
```python
def test_audit_chain_detects_tampering(tmp_path: Path) -> None
⋮----
path = tmp_path / "audit.jsonl"
audit = AuditLog(path)
⋮----
valid = verify_audit_chain(path)
⋮----
content = path.read_text(encoding="utf-8").replace('"x": 2', '"x": 999')
⋮----
broken = verify_audit_chain(path)
```

## File: test_audit_integrity.py
```python
def test_audit_integrity_accepts_valid_jsonl(tmp_path: Path) -> None
⋮----
path = tmp_path / "audit.jsonl"
⋮----
report = verify_jsonl_audit(path)
⋮----
def test_audit_integrity_rejects_invalid_jsonl(tmp_path: Path) -> None
```

## File: test_audit.py
```python
def test_audit_log_is_append_only(tmp_path: Path) -> None
⋮----
path = tmp_path / "audit.jsonl"
log = AuditLog(path)
⋮----
lines = path.read_text(encoding="utf-8").strip().splitlines()
⋮----
def test_build_audit_record_uses_supplied_previous_hash() -> None
⋮----
record = build_audit_record(
```

## File: test_backtest_ensemble.py
```python
def sample_market(n: int = 420) -> pd.DataFrame
⋮----
idx = pd.date_range("2020-01-01", periods=n, freq="D")
t = np.arange(n, dtype=float)
close = 100.0 + 0.05 * t + 5.0 * np.sin(t / 8.0) + 2.0 * np.sin(t / 2.7)
open_ = close * (1.0 + 0.0015 * np.sin(t / 4.0))
⋮----
def test_walk_forward_ensemble_runs() -> None
⋮----
report = WalkForwardBacktester(
```

## File: test_backtest.py
```python
def sample_market(n: int = 360) -> pd.DataFrame
⋮----
idx = pd.date_range("2020-01-01", periods=n, freq="D")
t = np.arange(n, dtype=float)
close = 100.0 + 0.04 * t + 4.0 * np.sin(t / 7.0) + 1.5 * np.sin(t / 2.3)
open_ = close * (1.0 + 0.001 * np.sin(t / 5.0))
⋮----
def test_walk_forward_produces_out_of_sample_report() -> None
⋮----
report = WalkForwardBacktester(
⋮----
def test_walk_forward_resets_daily_risk_baseline_between_dates(monkeypatch) -> None
⋮----
calls = 0
original = PaperBroker.reset_day_start
⋮----
def tracked_reset(self) -> None
⋮----
def test_regime_step_returns_are_compounded_without_intervening_equity() -> None
⋮----
result = _compound_step_returns([0.10, -0.05, 0.02])
⋮----
def test_walk_forward_annualizes_from_actual_oos_timestamps_by_default() -> None
⋮----
periods = infer_periods_per_year(report.equity_curve.index)
expected = compute_metrics(report.equity_curve, periods)
⋮----
def test_walk_forward_exits_position_after_hard_risk_stop(monkeypatch) -> None
⋮----
"""Backtest must account for a stop exit and its turnover/costs."""
decisions = 0
⋮----
def configured_risk(self, prediction, portfolio)
⋮----
rebalances: list[tuple[int, float]] = []
original_rebalance = PaperBroker.rebalance
⋮----
def tracked_rebalance(self, side, target_notional, price)
⋮----
endpoints = {
⋮----
0.001: (109.0, 107.0),  # Best validation, bad later holdout
0.005: (108.0, 116.0),  # Worse validation, attractive holdout
⋮----
def fake_backtest(self, market)
⋮----
equity = pd.Series(
⋮----
result = compare_rebalance_thresholds(
⋮----
better = self.risk_config.min_rebalance_fraction > 0.0
first_end = 109.0 if better else 106.0
last_end = 118.0 if better else 108.0
⋮----
def test_turnover_study_rejects_small_out_of_sample_history(monkeypatch) -> None
⋮----
calls: list[tuple[float, float, float]] = []
⋮----
config = self.risk_config
⋮----
endpoint = (
⋮----
study = compare_rebalance_thresholds(
⋮----
diagnostic = study["baseline_cost_sensitivity"]
⋮----
def test_turnover_study_does_not_repeat_frictionless_backtest(monkeypatch) -> None
```

## File: test_benchmark_gate.py
```python
metrics = PerformanceMetrics(
⋮----
def test_benchmark_gate_accepts_qualified_report() -> None
⋮----
result = evaluate_benchmark_gate(_report())
⋮----
def test_benchmark_gate_rejects_weak_out_of_sample_result() -> None
⋮----
result = evaluate_benchmark_gate(
⋮----
def test_benchmark_gate_rejects_net_loss_even_if_benchmark_loses_more() -> None
⋮----
report = _report(excess=0.20)
⋮----
decision = evaluate_benchmark_gate(report)
⋮----
def test_benchmark_gate_rejects_break_even_return_by_default() -> None
⋮----
report = _report()
⋮----
def test_benchmark_gate_rejects_nonfinite_metrics_that_skip_thresholds() -> None
⋮----
def test_benchmark_gate_rejects_infinite_annualized_volatility() -> None
```

## File: test_bootstrap_gate.py
```python
def test_bootstrap_gate_accepts_robust_distribution() -> None
⋮----
result = evaluate_bootstrap_gate(report())
⋮----
def test_bootstrap_gate_rejects_fragile_distribution() -> None
⋮----
result = evaluate_bootstrap_gate(
⋮----
# The research gate must fail closed on malformed bootstrap evidence.
invalid_cases = (
⋮----
decision = evaluate_bootstrap_gate(invalid)
```

## File: test_bootstrap_robustness.py
```python
def test_bootstrap_is_deterministic_with_seed() -> None
⋮----
curve = pd.Series([100.0, 101.0, 100.5, 102.0, 103.0, 104.0])
⋮----
first = bootstrap_equity_curve(
second = bootstrap_equity_curve(
⋮----
def test_bootstrap_rejects_too_short_curve() -> None
⋮----
def test_bootstrap_positive_curve_has_positive_median() -> None
⋮----
curve = pd.Series([100.0, 101.0, 102.0, 103.0, 104.0, 105.0])
⋮----
report = bootstrap_equity_curve(
⋮----
returns = np.linspace(-0.01, 0.02, length)
reference_rng = np.random.default_rng(123)
expected: list[float] = []
⋮----
start = int(reference_rng.integers(0, length - block_size + 1))
⋮----
actual_rng = np.random.default_rng(123)
actual = _block_bootstrap(returns, rng=actual_rng, block_size=block_size)
⋮----
# The next draw must also be identical: repeated bootstrap simulations
# rely on consuming exactly the same deterministic RNG sequence.
```

## File: test_broker.py
```python
def test_broker_resets_daily_loss_baseline_to_current_equity() -> None
⋮----
broker = PaperBroker(RiskConfig())
⋮----
@pytest.mark.parametrize("price", [0.0, -1.0, math.nan, math.inf, -math.inf])
def test_broker_rejects_invalid_mark_prices(price: float) -> None
⋮----
@pytest.mark.parametrize("side", [-2, 2, 99])
def test_broker_rejects_invalid_sides(side: int) -> None
⋮----
@pytest.mark.parametrize("notional", [-1.0, math.nan, math.inf])
def test_broker_rejects_invalid_target_notional(notional: float) -> None
⋮----
def test_opt_in_deadband_avoids_costly_same_side_micro_rebalances() -> None
⋮----
broker = PaperBroker(RiskConfig(min_rebalance_fraction=0.005))
opening = broker.rebalance(1, 10_000.0, 100.0)
⋮----
micro = broker.rebalance(1, 10_200.0, 100.0)
⋮----
meaningful = broker.rebalance(1, 11_000.0, 100.0)
⋮----
def test_deadband_never_blocks_stop_exit_or_position_flip() -> None
⋮----
broker = PaperBroker(RiskConfig(min_rebalance_fraction=1.0))
⋮----
flipped = broker.rebalance(-1, 1_000.0, 100.0)
⋮----
exited = broker.rebalance(0, 0.0, 100.0)
⋮----
def test_rebalance_deadband_is_disabled_by_default() -> None
⋮----
fill = broker.rebalance(1, 10_200.0, 100.0)
⋮----
@pytest.mark.parametrize("fraction", [-0.01, 1.01, math.nan, math.inf])
def test_invalid_rebalance_deadband_rejected(fraction: float) -> None
```

## File: test_burnin.py
```python
def test_burnin_tracker_persists_and_computes_metrics(tmp_path: Path) -> None
⋮----
tracker = BurnInTracker(tmp_path / "burnin.jsonl")
⋮----
snapshots = tracker.read()
```

## File: test_calibration_routing.py
```python
def test_calibration_penalty_reduces_weight_when_ece_is_high() -> None
⋮----
good = calibration_weight_multiplier(ece=0.02, observations=100)
bad = calibration_weight_multiplier(ece=0.30, observations=100)
⋮----
def test_calibration_penalty_waits_for_enough_observations() -> None
⋮----
weight = calibration_weight_multiplier(ece=0.50, observations=5)
```

## File: test_champion_probation.py
```python
BASELINE = {
⋮----
def seeded_registry(tmp_path: Path) -> tuple[ChampionRegistry, object]
⋮----
registry = ChampionRegistry(tmp_path / "champions.jsonl")
⋮----
champion = registry.promote(
⋮----
def test_probation_passes_after_enough_healthy_observations(tmp_path: Path) -> None
⋮----
store = ChampionProbationStore(tmp_path / "probation.json")
manager = ChampionProbationManager(
⋮----
first = manager.observe(BASELINE)
second = manager.observe(BASELINE)
⋮----
def test_probation_rolls_back_on_hard_drawdown_breach(tmp_path: Path) -> None
⋮----
result = manager.observe(
⋮----
degraded = {
⋮----
result = manager.observe(degraded)
⋮----
def test_probation_fails_closed_when_metrics_are_missing(tmp_path: Path) -> None
⋮----
result = manager.observe({"sharpe": 1.0})
⋮----
def test_probation_rollback_records_model_failure(tmp_path: Path) -> None
⋮----
quarantine = ModelQuarantineStore(tmp_path / "quarantine.json")
⋮----
record = quarantine.load()["v2"]
⋮----
def test_probation_success_clears_model_failures(tmp_path: Path) -> None
⋮----
result = manager.observe(BASELINE, processed_bar=100)
```

## File: test_champions.py
```python
def test_promote_and_rollback(tmp_path: Path) -> None
⋮----
registry = ChampionRegistry(tmp_path / "champions.jsonl")
first = registry.promote(
second = registry.promote(
⋮----
rolled = registry.rollback()
⋮----
def test_guarded_promotion_keeps_existing_champion_on_regression(tmp_path: Path) -> None
⋮----
def test_guarded_promotion_activates_qualified_challenger(tmp_path: Path) -> None
⋮----
def test_guarded_promotion_rejects_quarantined_version(tmp_path: Path) -> None
⋮----
quarantine = ModelQuarantineStore(tmp_path / "quarantine.json")
policy = QuarantinePolicy(failures_before_quarantine=1)
```

## File: test_chaos.py
```python
def market(n: int = 120) -> pd.DataFrame
⋮----
idx = pd.date_range("2026-01-01", periods=n, freq="D")
close = 100.0 + np.arange(n, dtype=float)
⋮----
def test_chaos_injects_ohlc_violation() -> None
⋮----
markets = {"GC=F": market()}
out = apply_chaos(
```

## File: test_checkpoint_verification.py
```python
def test_checkpoint_verification_detects_matching_state(tmp_path: Path) -> None
⋮----
state = tmp_path / "state.json"
audit_path = tmp_path / "audit.jsonl"
snapshot = tmp_path / "snapshots" / "one"
⋮----
audit = AuditLog(audit_path)
fingerprint = compute_session_fingerprint([state], audit_path)
⋮----
result = verify_checkpoint_state(
```

## File: test_cli_self_test.py
```python
runner = CliRunner()
⋮----
def test_self_test_command_runs_offline(tmp_path: Path) -> None
⋮----
workspace = tmp_path / "self-test"
⋮----
result = runner.invoke(
```

## File: test_cloudflare_scheduler_deploy_workflow.py
```python
def test_cloudflare_scheduler_deploy_workflow_is_fail_closed() -> None
⋮----
path = Path(".github/workflows/cloudflare-paper-scheduler-deploy.yml")
⋮----
text = path.read_text(encoding="utf-8")
⋮----
required = (
```

## File: test_compute_budget.py
```python
def test_compute_budget_sums_to_total_and_rewards_efficiency() -> None
⋮----
records = {
allocation = allocate_compute_budget(
```

## File: test_confidence_calibration.py
```python
def test_calibration_shrinks_overconfident_prediction() -> None
⋮----
record = QualityRecord(
prediction = Prediction(
⋮----
def test_calibration_leaves_short_history_unchanged() -> None
```

## File: test_config_validation.py
```python
def test_invalid_strategy_configuration_fails_closed(factory) -> None
⋮----
@pytest.mark.parametrize("alpha", [0.0, 1.0, -0.1, 1.1])
def test_expected_shortfall_rejects_invalid_alpha(alpha: float) -> None
⋮----
def test_global_allocator_rejects_negative_transaction_costs() -> None
⋮----
returns = pd.DataFrame({"A": [0.01, -0.01, 0.02]})
```

## File: test_control_plane.py
```python
def test_control_plane_halts_scheduler_on_governor_halt(tmp_path: Path) -> None
⋮----
governor = GovernorStateStore(tmp_path / "governor.json")
crisis = CrisisStateStore(tmp_path / "crisis.json")
⋮----
status = read_control_plane(
⋮----
lifecycle = LifecycleEventLog(tmp_path / "lifecycle.jsonl")
⋮----
resilience = ResilienceStateStore(tmp_path / "resilience.json")
```

## File: test_cost_stress_gate.py
```python
def test_cost_stress_gate_accepts_resilient_strategy() -> None
⋮----
gate = evaluate_cost_stress_gate(
⋮----
def test_cost_stress_gate_rejects_cost_fragility() -> None
⋮----
def test_cost_stress_gate_rejects_negative_net_returns_despite_positive_excess() -> None
⋮----
"""Beating a falling benchmark is not equivalent to making money."""
scenarios = tuple(
gate = evaluate_cost_stress_gate(scenarios)
⋮----
def test_cost_stress_gate_rejects_invalid_or_zero_trade_evidence() -> None
⋮----
scenarios = (
⋮----
def test_cost_stress_gate_counts_only_profitable_cost_scenarios() -> None
⋮----
def test_cost_stress_gate_rejects_loss_at_highest_cost_even_with_high_pass_ratio() -> None
⋮----
def test_cost_stress_gate_can_opt_out_of_worst_cost_requirement() -> None
```

## File: test_cost_stress.py
```python
class FakeBacktester
⋮----
def __init__(self, *, risk_config, model_config=None, config=None) -> None
⋮----
def run(self, df) -> BacktestReport
⋮----
bps = self.risk_config.transaction_cost_bps + self.risk_config.slippage_bps
total = 0.20 - bps / 1000.0
metrics = PerformanceMetrics(
curve = pd.Series([100.0, 101.0])
⋮----
def test_cost_stress_applies_each_cost_scenario(monkeypatch) -> None
⋮----
base = FakeBacktester(risk_config=RiskConfig())
scenarios = (
⋮----
results = run_cost_stress(base, pd.DataFrame(), scenarios=scenarios)
```

## File: test_crisis_controller.py
```python
def test_crisis_escalates_immediately_and_recovers_with_hysteresis() -> None
⋮----
policy = CrisisPolicy(recovery_confirmations=2)
decision = evaluate_crisis_state(
⋮----
hold = evaluate_crisis_state(
⋮----
recover = evaluate_crisis_state(
⋮----
def test_crisis_state_store_round_trip(tmp_path: Path) -> None
⋮----
store = CrisisStateStore(tmp_path / "crisis.json")
state = CrisisState(mode="defensive", recovery_streak=1)
```

## File: test_crisis_gate.py
```python
def test_promotions_are_frozen_outside_normal_mode(tmp_path: Path) -> None
⋮----
crisis = CrisisStateStore(tmp_path / "crisis.json")
governor = GovernorStateStore(tmp_path / "governor.json")
⋮----
def test_governor_freeze_blocks_promotions(tmp_path: Path) -> None
```

## File: test_cumulative_performance_persistence.py
```python
DATABASE_URL = os.environ["TEST_DATABASE_URL"]
RUNTIME_KEY = "paper:GC=F:5m:online-river:v1"
⋮----
def _state(processed_bars: int) -> RuntimeState
⋮----
def _trade(pnl: float, index: int) -> TradeSnapshot
⋮----
def _commit(revision: int, trade: TradeSnapshot) -> RuntimeStepCommit
⋮----
def _assert_metrics(metrics) -> None
⋮----
def test_postgres_persists_cumulative_trade_performance() -> None
⋮----
backend = PostgresPaperPersistence(DATABASE_URL)
⋮----
# Normalize the trade journal's 100k sleeve to its allocated paper capital.
allocated = backend.load_portfolio_trade_performance(
⋮----
def test_postgres_duplicate_trade_does_not_double_count_performance() -> None
⋮----
trade = _trade(12.5, 0)
⋮----
metrics = backend.load_trade_performance(RUNTIME_KEY)
⋮----
def test_postgres_schema_initialization_backfills_missing_performance_summary() -> None
⋮----
def test_file_backend_reports_full_journal_performance(tmp_path) -> None
⋮----
backend = FilePaperPersistence(root=tmp_path)
```

## File: test_dashboard_engine_status.py
```python
def test_dashboard_hides_expired_paper_decision(tmp_path) -> None
⋮----
# Fixed open Gold session: wall-clock maintenance windows must not alter the assertion.
now = datetime(2026, 9, 15, 19, 30, tzinfo=UTC)
journal = TradeJournal(tmp_path / "trades.jsonl")
state_store = RuntimeStateStore(tmp_path / "runtime_state.json")
status_store = HostedRuntimeStatusStore(tmp_path / "runtime_status.json")
⋮----
page = render_dashboard(
```

## File: test_dashboard_health.py
```python
def _free_port() -> int
⋮----
def _get(url: str) -> tuple[int, str, str]
⋮----
port = _free_port()
thread = Thread(
⋮----
deadline = time.time() + 3
⋮----
def test_dashboard_marks_expired_worker_heartbeat_stale(tmp_path) -> None
⋮----
journal = TradeJournal(tmp_path / "trades.jsonl")
state_store = RuntimeStateStore(tmp_path / "runtime_state.json")
status_store = HostedRuntimeStatusStore(tmp_path / "runtime_status.json")
⋮----
page = render_dashboard(
⋮----
def test_api_status_reports_stale_worker_without_hiding_web_health(tmp_path) -> None
⋮----
port = _start_dashboard(tmp_path)
⋮----
payload = json.loads(body)
⋮----
def test_healthz_keeps_web_liveness_separate_from_engine_health(tmp_path) -> None
⋮----
def test_external_probe_checks_live_ready_and_all_markets(tmp_path, monkeypatch) -> None
⋮----
deployed_sha = "a" * 40
⋮----
base_url = f"http://127.0.0.1:{port}"
⋮----
results = probe_dashboard(base_url, timeout=3, expected_sha=deployed_sha)
⋮----
mismatched = probe_dashboard(base_url, timeout=3, expected_sha="b" * 40)
⋮----
port = _start_dashboard(
⋮----
readiness = probe_dashboard(f"http://127.0.0.1:{port}", timeout=3)[1]
⋮----
def test_render_blueprint_declares_external_runtime_and_secret_inputs() -> None
⋮----
text = Path("render.yaml").read_text(encoding="utf-8")
⋮----
calls = []
⋮----
def fail_request(request, timeout)
⋮----
results = probe_dashboard("https://example.invalid")
⋮----
# Exactly one short retry per unreachable endpoint, no secret disclosure.
⋮----
def test_probe_rejects_market_cards_with_broken_portfolio(monkeypatch) -> None
⋮----
class FakeResponse
⋮----
status = 200
⋮----
def __init__(self, payload)
⋮----
def __enter__(self)
⋮----
def __exit__(self, *args)
⋮----
def read(self, count)
⋮----
livez_calls = 0
⋮----
def fake_urlopen(request, timeout)
⋮----
"""An all-STARTING service must not pass the production health probe."""
⋮----
statuses = {"GC=F": "STARTING", "^GDAXI": "STARTING", "BTC-USD": "STARTING"}
cycle_errors = {"GC=F": 0, "^GDAXI": 0, "BTC-USD": 0}
⋮----
base = "https://example.invalid"
cards_only = probe_dashboard(base)
assert cards_only[2].ok is True  # Backward-compatible card-level check.
⋮----
starting = probe_dashboard(base, require_running_markets=True)
⋮----
healthy = probe_dashboard(base, require_running_markets=True)
⋮----
degraded = probe_dashboard(base, require_running_markets=True)
⋮----
stale = probe_dashboard(base, require_running_markets=True)
```

## File: test_dashboard_overview.py
```python
RUNTIME_KEY = "paper:GC=F:5m:online-river:v1"
⋮----
class OverviewPersistence
⋮----
def load_runtime(self, runtime_key: str, starting_cash: float) -> PersistedRuntime
⋮----
def list_trades(self, runtime_key: str | None = None, *, limit: int | None = None)
⋮----
def list_burnin_snapshots(self, runtime_key: str)
⋮----
def list_regimes(self, runtime_key: str) -> tuple[str, ...]
⋮----
def load_runtime_status(self, runtime_key: str) -> HostedRuntimeStatus | None
⋮----
def load_trade_performance(self, runtime_key: str)
⋮----
def load_shadow_quality(self, runtime_key: str) -> ShadowQualityComparison
⋮----
river = ModelQuality(
challenger = ModelQuality(
⋮----
class ReadinessOverviewPersistence(OverviewPersistence)
⋮----
class FailingOverviewPersistence
⋮----
def load_runtime(self, runtime_key: str, starting_cash: float)
⋮----
def load_runtime_status(self, runtime_key: str)
⋮----
def _free_port() -> int
⋮----
def _start_overview_dashboard(persistence: OverviewPersistence) -> int
⋮----
port = _free_port()
thread = Thread(
⋮----
deadline = time.time() + 3
⋮----
def test_operational_overview_exposes_model_and_runtime_metadata() -> None
⋮----
payload = build_operational_overview(OverviewPersistence(), RUNTIME_KEY)
⋮----
mtf_gate = payload["mtf_shadow_challenger"]["promotion_gate"]
⋮----
gate = payload["shadow_challenger"]["promotion_gate"]
⋮----
def test_operational_overview_flags_stale_runtime() -> None
⋮----
payload = build_operational_overview(
⋮----
def test_operational_overview_flags_missing_model_after_processing() -> None
⋮----
def test_operational_overview_flags_inconsistent_runtime() -> None
⋮----
persistence = OverviewPersistence()
⋮----
payload = build_operational_overview(persistence, RUNTIME_KEY)
⋮----
def test_operational_overview_storage_failure_is_sanitized() -> None
⋮----
payload = build_operational_overview(FailingOverviewPersistence(), RUNTIME_KEY)
⋮----
def test_dashboard_exposes_operational_overview_endpoint() -> None
⋮----
port = _start_overview_dashboard(OverviewPersistence())
⋮----
payload = json.loads(response.read().decode())
⋮----
def test_dashboard_renders_model_and_revision_metadata(tmp_path) -> None
⋮----
page = render_dashboard(
⋮----
def test_dashboard_renders_operational_alerts(tmp_path) -> None
⋮----
def test_dashboard_renders_inconsistent_runtime_alert(tmp_path) -> None
⋮----
def test_operational_overview_flags_cycle_reliability_degradation() -> None
⋮----
def test_dashboard_renders_cycle_reliability_alert(tmp_path) -> None
⋮----
def test_operational_overview_exposes_structured_readiness() -> None
⋮----
payload = build_operational_overview(ReadinessOverviewPersistence(), RUNTIME_KEY)
⋮----
readiness = payload["readiness"]
⋮----
burnin = next(
⋮----
def test_overview_endpoint_includes_readiness_evidence() -> None
⋮----
port = _start_overview_dashboard(ReadinessOverviewPersistence())
⋮----
class BtcOverviewPersistence(OverviewPersistence)
⋮----
def list_regimes(self, runtime_key: str)
⋮----
def load_mtf_shadow_quality(self, runtime_key: str, **kwargs)
⋮----
def test_btc_overview_exposes_validated_mtf_candidate() -> None
⋮----
mtf = payload["mtf_shadow_challenger"]
⋮----
class NoMeasuredPnlOverviewPersistence(OverviewPersistence)
⋮----
def test_operational_overview_does_not_expose_unknown_pnl_as_zero() -> None
⋮----
performance = payload["performance"]
```

## File: test_dashboard_persistence.py
```python
RUNTIME_KEY = "paper:GC=F:5m:online-river:v1"
⋮----
class DurablePersistence
⋮----
def __init__(self) -> None
⋮----
def load_runtime(self, runtime_key: str, starting_cash: float) -> PersistedRuntime
⋮----
def list_trades(self, runtime_key: str | None = None, *, limit: int | None = None)
⋮----
def load_trade_performance(self, runtime_key: str)
⋮----
def list_burnin_snapshots(self, runtime_key: str)
⋮----
def list_regimes(self, runtime_key: str) -> tuple[str, ...]
⋮----
def load_runtime_status(self, runtime_key: str) -> HostedRuntimeStatus | None
⋮----
def list_scheduler_deliveries(self, *, limit: int = 20)
⋮----
now = datetime.now(UTC)
⋮----
class FailingPersistence
⋮----
def _fail(self)
⋮----
def load_runtime(self, runtime_key: str, starting_cash: float)
⋮----
def load_runtime_status(self, runtime_key: str)
⋮----
def _free_port() -> int
⋮----
def _get(url: str) -> tuple[int, str]
⋮----
def _get_with_headers(url: str)
⋮----
def _start_failure_dashboard() -> int
⋮----
port = _free_port()
thread = Thread(
⋮----
deadline = time.time() + 3
⋮----
def test_dashboard_uses_durable_state_trades_and_status(tmp_path) -> None
⋮----
journal = TradeJournal(tmp_path / "empty.jsonl")
⋮----
page = render_dashboard(
⋮----
def test_dashboard_storage_failure_is_sanitized(tmp_path) -> None
⋮----
def test_liveness_stays_healthy_when_storage_is_unavailable() -> None
⋮----
port = _start_failure_dashboard()
⋮----
def test_readiness_fails_when_durable_storage_is_unavailable() -> None
⋮----
def test_status_endpoints_fail_closed_without_leaking_storage_details() -> None
⋮----
status_payload = json.loads(status_body)
health_payload = json.loads(health_body)
⋮----
def test_dashboard_surfaces_verified_scheduler_delivery(tmp_path) -> None
⋮----
def test_dashboard_http_responses_include_security_headers() -> None
⋮----
def test_dashboard_v2_groups_critical_sections_and_renders_equity_chart(tmp_path) -> None
⋮----
def test_dashboard_premium_shell_and_navigation(tmp_path) -> None
⋮----
def test_dashboard_quant_evidence_is_explicit_and_non_misleading(tmp_path) -> None
⋮----
class ReadinessPersistence(DurablePersistence)
⋮----
def test_dashboard_readiness_panel_shows_eight_criteria_with_thresholds(tmp_path) -> None
```

## File: test_dashboard.py
```python
def test_trade_journal_round_trip(tmp_path) -> None
⋮----
journal = TradeJournal(tmp_path / "trades.jsonl")
trade = TradeSnapshot(
⋮----
def test_dashboard_renders_trade_and_escapes_text(tmp_path) -> None
⋮----
page = render_dashboard(journal)
⋮----
def test_trade_journal_limit_returns_latest_events(tmp_path) -> None
⋮----
def test_dashboard_renders_portfolio_summary(tmp_path) -> None
⋮----
def test_dashboard_renders_recent_trade_performance_metrics(tmp_path) -> None
⋮----
def test_dashboard_renders_premium_terminal_shell(tmp_path) -> None
⋮----
page = render_dashboard(TradeJournal(tmp_path / "empty.jsonl"))
⋮----
def test_dashboard_live_refresh_preserves_scroll_without_meta_reload(tmp_path) -> None
⋮----
def test_dashboard_does_not_render_legacy_unknown_pnl_as_zero(tmp_path) -> None
⋮----
def test_scheduler_display_state_reports_waiting_collecting_stale_and_verified() -> None
⋮----
base = {
⋮----
waiting = _scheduler_display_state(base)
collecting = _scheduler_display_state(
stale = _scheduler_display_state(
degraded = _scheduler_display_state(
verified = _scheduler_display_state(
```

## File: test_data_quality.py
```python
def clean_market(n: int = 120) -> pd.DataFrame
⋮----
idx = pd.date_range("2026-01-01", periods=n, freq="D")
close = 100.0 + np.arange(n, dtype=float) * 0.1
⋮----
def test_clean_market_data_scores_high() -> None
⋮----
report = evaluate_market_data_quality(clean_market())
⋮----
def test_invalid_ohlc_is_detected() -> None
⋮----
df = clean_market()
⋮----
report = evaluate_market_data_quality(df)
⋮----
def test_missing_required_column_fails_closed() -> None
⋮----
report = evaluate_market_data_quality(clean_market().drop(columns=["Open"]))
⋮----
def intraday_market(n: int = 120) -> pd.DataFrame
⋮----
frame = clean_market(n)
⋮----
def test_occasional_cadence_gap_is_tolerated() -> None
⋮----
df = intraday_market().drop(index=intraday_market().index[50])
⋮----
def test_repeated_cadence_gaps_fail_quality_gate() -> None
⋮----
df = intraday_market()
df = df.drop(index=df.index[10:110:10])
⋮----
def test_non_datetime_index_fails_cadence_quality() -> None
⋮----
def test_data_quality_rejects_invalid_scoring_configuration(kwargs) -> None
⋮----
def test_single_session_break_in_recent_intraday_window_is_tolerated() -> None
⋮----
df = intraday_market(120)
before = df.iloc[:60].copy()
after = df.iloc[60:].copy()
⋮----
session_split = pd.concat([before, after])
⋮----
report = evaluate_market_data_quality(session_split)
```

## File: test_data.py
```python
def test_load_history_keeps_price_rows_when_volume_is_missing(monkeypatch) -> None
⋮----
index = pd.date_range("2026-09-18 08:00", periods=60, freq="5min")
frame = pd.DataFrame(
⋮----
loaded = data_module.load_history("^GDAXI", period="5d", interval="5m")
⋮----
def test_load_history_retries_transient_provider_failure(monkeypatch) -> None
⋮----
index = pd.date_range("2026-09-18 08:00", periods=3, freq="5min")
⋮----
calls = {"count": 0}
⋮----
def flaky_download(*args, **kwargs)
⋮----
loaded = data_module.load_history(
⋮----
def test_load_history_sorts_and_deduplicates_provider_rows(monkeypatch) -> None
⋮----
index = pd.to_datetime(
⋮----
loaded = data_module.load_history("GC=F", max_attempts=1)
⋮----
def test_load_history_rejects_inconsistent_ohlc(monkeypatch) -> None
⋮----
index = pd.date_range("2026-09-18 08:00", periods=2, freq="5min")
⋮----
class _Provider
⋮----
def __init__(self, name: str, result) -> None
⋮----
def download(self, symbol: str, *, period: str, interval: str) -> pd.DataFrame
⋮----
def test_load_history_falls_back_to_next_provider_after_primary_exhaustion(monkeypatch) -> None
⋮----
primary = _Provider("primary", RuntimeError("provider unavailable"))
fallback = _Provider("fallback", frame)
⋮----
def test_load_history_rejects_empty_provider_chain() -> None
```

## File: test_dataset_evidence.py
```python
def market() -> pd.DataFrame
⋮----
index = pd.date_range("2025-01-01", periods=4, freq="D")
⋮----
def test_dataset_hash_is_deterministic() -> None
⋮----
first = build_dataset_evidence(market())
second = build_dataset_evidence(market())
⋮----
def test_single_ohlcv_change_changes_dataset_hash() -> None
⋮----
original = market()
modified = original.copy()
⋮----
def test_timestamp_change_changes_dataset_hash() -> None
⋮----
def test_provenance_changes_evidence_identity() -> None
⋮----
frame = market()
first = build_dataset_evidence(
second = build_dataset_evidence(
```

## File: test_deployment_readiness.py
```python
def qualified_record() -> QualificationRecord
⋮----
def composite_score()
⋮----
def stable_trend() -> ReadinessTrend
⋮----
def reliable_report() -> ReliabilityReport
⋮----
def test_deployment_readiness_allows_only_fully_healthy_state() -> None
⋮----
result = evaluate_deployment_readiness(
⋮----
def test_deployment_readiness_fails_closed_on_resilience_or_governor() -> None
⋮----
def test_deployment_readiness_rejects_short_reliability_history() -> None
⋮----
reliability = reliable_report()
reliability = ReliabilityReport(
⋮----
def test_deployment_readiness_rejects_missing_composite_score() -> None
⋮----
def test_deployment_readiness_rejects_unstable_trend() -> None
⋮----
trend = ReadinessTrend(
⋮----
def test_deployment_readiness_rejects_invalid_readiness_chain() -> None
⋮----
def test_deployment_readiness_rejects_invalid_release_manifest() -> None
⋮----
def test_deployment_readiness_rejects_non_reproducible_quantitative_evidence() -> None
⋮----
def test_deployment_readiness_rejects_stale_quantitative_evidence() -> None
⋮----
def test_deployment_readiness_rejects_unknown_quantitative_evidence_age() -> None
⋮----
def test_deployment_readiness_accepts_dataset_observation_at_age_limit() -> None
⋮----
def test_deployment_readiness_rejects_stale_dataset_observation() -> None
⋮----
def test_deployment_readiness_rejects_unknown_dataset_observation_age() -> None
```

## File: test_distribution_drift.py
```python
def frame(seed: int, shift: float = 0.0, n: int = 300) -> pd.DataFrame
⋮----
rng = np.random.default_rng(seed)
⋮----
def test_distribution_drift_detects_shifted_features() -> None
⋮----
reference = frame(1, 0.0)
recent = frame(2, 2.0, n=100)
report = detect_distribution_drift(reference, recent)
⋮----
def test_distribution_drift_stays_low_for_similar_samples() -> None
⋮----
reference = frame(3, 0.0)
recent = reference.iloc[-100:].copy()
```

## File: test_drift_retrain_store.py
```python
def test_drift_retrain_store_enforces_cooldown(tmp_path: Path) -> None
⋮----
store = DriftRetrainStore(tmp_path / "drift.json")
```

## File: test_drift.py
```python
def frame(mean_shift: float, n: int) -> pd.DataFrame
⋮----
rng = np.random.default_rng(7)
⋮----
def test_detects_material_feature_drift() -> None
⋮----
reference = frame(0.0, 200)
recent = frame(3.0, 80)
report = detect_drift(
⋮----
def test_no_drift_for_similar_distributions() -> None
⋮----
rng = np.random.default_rng(11)
reference = pd.DataFrame({name: rng.normal(0, 1, 200) for name in FEATURES})
recent = pd.DataFrame({name: rng.normal(0, 1, 80) for name in FEATURES})
```

## File: test_durable_burnin_persistence.py
```python
DATABASE_URL = os.environ["TEST_DATABASE_URL"]
RUNTIME_KEY = "paper:GC=F:5m:online-river:v1"
⋮----
def _commit(*, revision: int, cash: float, units: float, price: float) -> RuntimeStepCommit
⋮----
processed_bars = revision + 1
state = RuntimeState(
⋮----
def _assert_snapshots(snapshots) -> None
⋮----
def test_postgres_records_one_equity_snapshot_per_committed_bar() -> None
⋮----
backend = PostgresPaperPersistence(DATABASE_URL)
⋮----
commits = (
⋮----
def test_postgres_conflict_does_not_append_burnin_snapshot() -> None
⋮----
snapshots = backend.list_burnin_snapshots(RUNTIME_KEY)
⋮----
def test_file_backend_records_equity_snapshots_per_commit(tmp_path) -> None
⋮----
backend = FilePaperPersistence(root=tmp_path)
⋮----
def test_burnin_tracker_uses_processed_bars_for_readiness_duration(tmp_path) -> None
⋮----
tracker = BurnInTracker(tmp_path / "burnin.jsonl")
⋮----
report = tracker.readiness()
```

## File: test_economic_meta_store.py
```python
def test_economic_meta_store_persists_updates(tmp_path: Path) -> None
⋮----
store = EconomicMetaStore(tmp_path / "economic.json")
updated = store.update(
loaded = store.load()["GC=F|river|bull"]
```

## File: test_economic_meta.py
```python
def test_profitable_low_cost_model_scores_better() -> None
⋮----
base = EconomicMetaStats()
good = update_economic_meta(
bad = update_economic_meta(
```

## File: test_ensemble.py
```python
def sample_training(n: int = 180) -> tuple[pd.DataFrame, pd.Series]
⋮----
t = np.arange(n, dtype=float)
x = pd.DataFrame(
y = pd.Series(np.where(x["trend_10"] > 0.008, 1, np.where(x["trend_10"] < -0.008, -1, 0)))
⋮----
def test_ensemble_returns_valid_probability_distribution() -> None
⋮----
model = EnsembleDirectionModel(random_state=7)
⋮----
pred = model.predict_one(
⋮----
def test_ensemble_accepts_explicit_feature_set() -> None
⋮----
x = x.copy()
⋮----
feature_names = [*FEATURES, "extra_momentum"]
⋮----
model = EnsembleDirectionModel(random_state=11, feature_names=feature_names)
```

## File: test_evolution_manager.py
```python
def market(n: int = 360) -> pd.DataFrame
⋮----
idx = pd.date_range("2023-01-01", periods=n, freq="D")
t = np.arange(n, dtype=float)
close = 100 + 0.05 * t + 3.0 * np.sin(t / 8.0)
open_ = close * (1.0 + 0.001 * np.sin(t / 5.0))
⋮----
def test_evolution_cycle_mutates_top_parent(tmp_path) -> None
⋮----
store = ExpertPoolStore(tmp_path / "pool.json")
⋮----
result = run_evolution_cycle(
```

## File: test_evolution.py
```python
def test_mutation_generates_distinct_variants() -> None
⋮----
parent = ExpertCandidate(
children = mutate_expert(
```

## File: test_execution_costs.py
```python
def test_execution_cost_override_is_symbol_specific() -> None
⋮----
raw = """
base = RiskConfig(transaction_cost_bps=2.0, slippage_bps=1.0)
⋮----
gold = risk_config_for_symbol("GC=F", base, raw=raw)
dax = risk_config_for_symbol("^GDAXI", base, raw=raw)
⋮----
def test_execution_cost_override_can_be_partial() -> None
⋮----
updated = risk_config_for_symbol(
⋮----
def test_execution_cost_overrides_fail_closed_on_invalid_configuration(raw: str) -> None
⋮----
def test_default_runtime_uses_symbol_cost_override(monkeypatch, tmp_path) -> None
⋮----
runtime = PaperAutonomousRuntime(
⋮----
def test_explicit_runtime_risk_config_has_priority(monkeypatch, tmp_path) -> None
⋮----
explicit = RiskConfig(transaction_cost_bps=9.0, slippage_bps=10.0)
```

## File: test_expert_diversity.py
```python
def test_diversity_rejects_nearly_identical_experts() -> None
⋮----
x = np.linspace(-0.02, 0.02, 100)
df = pd.DataFrame({"a": x, "b": x * 1.001})
report = evaluate_expert_diversity(df, max_pair_correlation=0.8)
⋮----
def test_diversity_accepts_low_correlation_experts() -> None
⋮----
rng = np.random.default_rng(7)
df = pd.DataFrame(
```

## File: test_expert_factory.py
```python
def market(n: int = 260) -> pd.DataFrame
⋮----
idx = pd.date_range("2024-01-01", periods=n, freq="D")
t = np.arange(n, dtype=float)
close = 100 + 0.03 * t + 4.0 * np.sin(t / 10.0)
open_ = close * (1.0 + 0.001 * np.sin(t / 4.0))
⋮----
def test_generate_candidates_respects_cap() -> None
⋮----
candidates = generate_candidates(
⋮----
def test_factory_evaluates_and_persists_candidates(tmp_path) -> None
⋮----
store = ExpertPoolStore(tmp_path / "pool.json")
result = run_expert_factory(
```

## File: test_expert_horizon.py
```python
def test_factory_propagates_candidate_horizon(tmp_path, monkeypatch) -> None
⋮----
seen: list[int] = []
```

## File: test_expert_lifecycle.py
```python
def test_expert_lifecycle_retires_persistently_bad_expert() -> None
⋮----
stats = EconomicMetaStats(score=-0.05, observations=30)
decision = evaluate_expert_lifecycle(stats)
⋮----
def test_expert_lifecycle_retrains_mildly_degraded_expert() -> None
⋮----
stats = EconomicMetaStats(score=-0.01, observations=30)
decision = evaluate_expert_lifecycle(
⋮----
def test_expert_lifecycle_keeps_early_expert() -> None
⋮----
stats = EconomicMetaStats(score=-1.0, observations=3)
```

## File: test_expert_pool_manager.py
```python
def market(n: int = 240) -> pd.DataFrame
⋮----
idx = pd.date_range("2024-01-01", periods=n, freq="D")
t = np.arange(n, dtype=float)
close = 100 + 0.04 * t + 3.5 * np.sin(t / 9.0)
open_ = close * (1.0 + 0.001 * np.sin(t / 4.0))
⋮----
def test_refresh_expert_pool_evaluates_all_specialists(tmp_path) -> None
⋮----
store = ExpertPoolStore(tmp_path / "pool.json")
result = refresh_expert_pool(
```

## File: test_expert_pool.py
```python
def test_pool_promotes_best_validated_challenger_and_caps_active() -> None
⋮----
records = {
reconciled = reconcile_pool(
⋮----
def test_pool_prunes_persistently_bad_expert() -> None
⋮----
reconciled = reconcile_pool(records)
⋮----
def test_compute_budget_rewards_quality_per_compute_cost() -> None
⋮----
weights = compute_budget_weights(records)
```

## File: test_expert_sandbox.py
```python
def market(n: int = 220) -> pd.DataFrame
⋮----
idx = pd.date_range("2024-01-01", periods=n, freq="D")
t = np.arange(n, dtype=float)
close = 100 + 0.05 * t + 3.0 * np.sin(t / 8.0)
open_ = close * (1.0 + 0.001 * np.sin(t / 3.0))
⋮----
def test_specialist_sandbox_returns_validation_score() -> None
⋮----
result = validate_specialist(market(), kind="trend", train_fraction=0.65)
```

## File: test_expert_uncertainty.py
```python
def prediction(side: int, probs: dict[int, float]) -> Prediction
⋮----
def test_identical_experts_have_zero_disagreement() -> None
⋮----
pred = prediction(1, {-1: 0.1, 0: 0.1, 1: 0.8})
report = measure_expert_uncertainty({"a": pred, "b": pred})
⋮----
def test_conflicting_experts_reduce_risk_multiplier() -> None
⋮----
long = prediction(1, {-1: 0.0, 0: 0.0, 1: 1.0})
short = prediction(-1, {-1: 1.0, 0: 0.0, 1: 0.0})
report = measure_expert_uncertainty({"long": long, "short": short})
```

## File: test_features.py
```python
def sample_df(n: int = 100) -> pd.DataFrame
⋮----
idx = pd.date_range("2025-01-01", periods=n, freq="D")
close = pd.Series(100 + np.linspace(0, 20, n) + np.sin(np.arange(n)), index=idx)
⋮----
def test_features_have_expected_columns() -> None
⋮----
x = make_features(sample_df())
⋮----
def test_labels_only_three_classes() -> None
⋮----
y = make_labels(sample_df(), return_threshold=0.002).dropna().astype(int)
⋮----
def test_challenger_features_extend_production_features_without_replacing_them() -> None
⋮----
base = make_features(sample_df())
challenger = make_challenger_features(sample_df())
⋮----
def test_volume_less_market_keeps_neutral_volume_features() -> None
⋮----
df = sample_df()
⋮----
base = make_features(df)
challenger = make_challenger_features(df)
```

## File: test_file_persistence.py
```python
def test_file_backend_survives_new_instance(tmp_path) -> None
⋮----
backend = FilePaperPersistence(root=tmp_path)
key = "paper:GC=F:5m:online-river:v1"
loaded = backend.load_runtime(key, 100_000.0)
⋮----
outcome = backend.commit_step(
⋮----
restored = FilePaperPersistence(root=tmp_path).load_runtime(key, 100_000.0)
⋮----
def test_file_backend_rejects_stale_revision(tmp_path) -> None
⋮----
commit = RuntimeStepCommit(
⋮----
def test_file_backend_persists_unique_regimes(tmp_path) -> None
⋮----
first = RuntimeStepCommit(
second = RuntimeStepCommit(
⋮----
restored = FilePaperPersistence(root=tmp_path)
⋮----
def test_file_backend_loads_shadow_quality_from_audit(tmp_path) -> None
⋮----
payloads = [
⋮----
comparison = backend.load_shadow_quality("paper:GC=F:5m:online-river:v1")
⋮----
def test_file_backend_persists_scheduler_deliveries(tmp_path) -> None
⋮----
delivery = SchedulerDelivery(
```

## File: test_generation_progress.py
```python
def test_generation_progress_detects_improvement() -> None
⋮----
previous = GenerationSnapshot(
current = GenerationSnapshot(
progress = compare_generations(previous, current)
```

## File: test_generation_rollback.py
```python
def test_generation_rollback_restores_previous_active_set(tmp_path: Path) -> None
⋮----
pool = ExpertPoolStore(tmp_path / "pool.json")
generations = GenerationStore(
⋮----
result = rollback_generation(pool, generations)
records = pool.load()
```

## File: test_generations.py
```python
def test_generation_store_tracks_lineage_and_snapshots(tmp_path: Path) -> None
⋮----
store = GenerationStore(
lineage = store.add_lineage("child", "parent", 1)
⋮----
first = store.snapshot(["parent"], 0.5)
second = store.snapshot(["child"], 0.7)
```

## File: test_global_allocator.py
```python
def test_expected_shortfall_is_positive_for_lossy_tail() -> None
⋮----
returns = pd.Series([0.01, 0.02, -0.03, -0.02, 0.005, -0.04])
es = expected_shortfall(returns, alpha=0.8)
⋮----
def test_global_allocator_respects_expert_caps_and_reports_turnover() -> None
⋮----
rng = np.random.default_rng(7)
cols = [
returns = pd.DataFrame(
report = allocate_global_capital(
```

## File: test_global_selection.py
```python
def test_global_generation_requires_score_and_diversity() -> None
⋮----
good = evaluate_global_generation(
⋮----
bad_diversity = evaluate_global_generation(
⋮----
bad_score = evaluate_global_generation(
```

## File: test_governor_state_store.py
```python
def test_governor_state_store_round_trip(tmp_path: Path) -> None
⋮----
store = GovernorStateStore(tmp_path / "governor.json")
state = GovernorState(verdict="FREEZE", reason="test", consecutive_halts=2)
```

## File: test_guardrails.py
```python
def metrics(sharpe: float = 1.0, drawdown: float = 0.08) -> PerformanceMetrics
⋮----
def test_health_rolls_back_on_drift() -> None
⋮----
drift = DriftReport(2.0, 0.1, True, ("feature distribution drift",))
decision = evaluate_health(metrics(), drift)
⋮----
def test_health_accepts_healthy_model() -> None
⋮----
drift = DriftReport(0.1, 0.1, False, ())
decision = evaluate_health(metrics(), drift, HealthPolicy(min_sharpe=0.5, max_drawdown=0.10))
```

## File: test_health_server.py
```python
def test_health_server_exposes_metrics() -> None
⋮----
server = HealthServer(host="127.0.0.1", port=0)
⋮----
port = server.server.server_address[1]
⋮----
body = response.read().decode("utf-8")
⋮----
def test_health_server_returns_not_found_for_unknown_route() -> None
```

## File: test_hosted_persistence.py
```python
RUNTIME_KEY = "paper:GC=F:5m:online-river:v1"
⋮----
class RecordingPersistence
⋮----
def __init__(self) -> None
⋮----
def save_runtime_status(self, runtime_key: str, status: HostedRuntimeStatus) -> None
⋮----
def load_runtime_status(self, runtime_key: str) -> HostedRuntimeStatus | None
⋮----
def _settings() -> HostedPaperSettings
⋮----
def _raising_scheduler(monkeypatch) -> None
⋮----
class RaisingScheduler
⋮----
def __init__(self, **kwargs) -> None
⋮----
def run(self) -> None
⋮----
def _fake_runtime(monkeypatch) -> None
⋮----
def test_hosted_settings_exposes_stable_runtime_key() -> None
⋮----
def test_hosted_loop_shares_backend_and_runtime_key(monkeypatch) -> None
⋮----
persistence = RecordingPersistence()
captured: dict[str, object] = {}
⋮----
def fake_runtime(**kwargs)
⋮----
class FakeScheduler
⋮----
def run(self) -> list[object]
⋮----
runtime_kwargs = captured["runtime_kwargs"]
⋮----
def test_hosted_loop_persists_error_status(monkeypatch) -> None
⋮----
def test_worker_error_is_not_masked_when_status_storage_is_unavailable(monkeypatch) -> None
⋮----
class FailingStatusPersistence(RecordingPersistence)
⋮----
persistence = FailingStatusPersistence()
⋮----
def test_start_worker_can_reuse_injected_backend() -> None
⋮----
seen: list[tuple[HostedPaperSettings, object]] = []
⋮----
def runner(settings: HostedPaperSettings, *, persistence) -> None
⋮----
thread = hosted_runtime.start_hosted_paper_runtime(
```

## File: test_hosted_runtime.py
```python
def test_hosted_paper_settings_disabled_by_default(monkeypatch) -> None
⋮----
settings = HostedPaperSettings.from_env()
⋮----
def test_enabled_hosted_runtime_starts_daemon_worker(monkeypatch) -> None
⋮----
called = Event()
seen: list[HostedPaperSettings] = []
⋮----
def runner(settings: HostedPaperSettings) -> None
⋮----
thread = start_hosted_paper_runtime(runner=runner)
⋮----
def test_external_scheduler_suppresses_daemon(monkeypatch) -> None
⋮----
thread = start_hosted_paper_runtime(settings=settings, runner=lambda _: None)
⋮----
def test_hosted_loop_disables_expensive_health_check(monkeypatch) -> None
⋮----
captured: dict[str, object] = {}
⋮----
class FakePersistence
⋮----
def __init__(self) -> None
⋮----
def save_runtime_status(self, runtime_key, status) -> None
⋮----
def load_runtime_status(self, runtime_key)
⋮----
class FakeScheduler
⋮----
def __init__(self, **kwargs) -> None
⋮----
def run(self) -> list[object]
⋮----
fake_runtime = SimpleNamespace(
⋮----
config = captured["config"]
⋮----
def test_hosted_settings_enable_shadow_challenger(monkeypatch) -> None
⋮----
def test_hosted_settings_read_separate_mtf_period(monkeypatch) -> None
```

## File: test_lifecycle_log.py
```python
def test_lifecycle_log_hashes_artifact_and_appends_events(tmp_path: Path) -> None
⋮----
artifact = tmp_path / "model.joblib"
⋮----
log = LifecycleEventLog(tmp_path / "lifecycle.jsonl")
⋮----
first = log.append(
second = log.append(
⋮----
records = log.list()
```

## File: test_maintenance.py
```python
def test_maintenance_round_trip(tmp_path: Path) -> None
⋮----
store = MaintenanceStore(tmp_path / "maintenance.json")
state = MaintenanceState(enabled=True, reason="upgrade")
```

## File: test_marginal_alpha.py
```python
def test_marginal_alpha_accepts_diversifying_profitable_candidate() -> None
⋮----
rng = np.random.default_rng(3)
portfolio = pd.Series(rng.normal(0.0002, 0.01, 300))
candidate = pd.Series(rng.normal(0.0008, 0.008, 300))
report = evaluate_marginal_alpha(
⋮----
def test_marginal_alpha_rejects_identical_candidate_on_correlation() -> None
⋮----
rng = np.random.default_rng(4)
portfolio = pd.Series(rng.normal(0.0004, 0.01, 300))
```

## File: test_market_freshness.py
```python
def test_btc_session_is_always_open() -> None
⋮----
saturday = datetime(2026, 9, 19, 12, 0, tzinfo=UTC)
⋮----
approved = replace(
valid = paper_signal_snapshot(
⋮----
expired = paper_signal_snapshot(
⋮----
def test_dax_regular_weekday_session_is_dst_aware() -> None
⋮----
opening = datetime(2026, 9, 21, 7, 0, tzinfo=UTC)
after_close = datetime(2026, 9, 21, 16, 0, tzinfo=UTC)
⋮----
def test_gold_daily_maintenance_window_is_closed() -> None
⋮----
maintenance = datetime(2026, 9, 21, 21, 30, tzinfo=UTC)
reopened = datetime(2026, 9, 21, 22, 30, tzinfo=UTC)
⋮----
def test_gold_weekend_is_closed() -> None
⋮----
def test_catch_up_takes_priority_over_live_state() -> None
⋮----
status = _status(reason="catch-up pending")
⋮----
def test_known_data_gap_is_exposed_as_provider_gap_while_market_open() -> None
⋮----
status = _status(
⋮----
def test_closed_session_is_not_misreported_as_delayed() -> None
⋮----
status = _status()
⋮----
blocked = paper_signal_snapshot(
⋮----
def test_stale_heartbeat_during_open_session_is_delayed() -> None
```

## File: test_meta_router.py
```python
def test_meta_router_prefers_contextually_better_model() -> None
⋮----
long = Prediction(1, 0.8, {-1: 0.1, 0: 0.1, 1: 0.8})
short = Prediction(-1, 0.8, {-1: 0.8, 0: 0.1, 1: 0.1})
routed = route_predictions(
⋮----
def test_meta_context_is_constructible() -> None
⋮----
context = MetaContext(
```

## File: test_meta_store.py
```python
def test_meta_store_learns_context_specific_scores(tmp_path: Path) -> None
⋮----
store = MetaRouterStore(tmp_path / "meta.json")
context = MetaContext("GC=F", "bull_normal_vol", "normal", "low")
⋮----
scores = store.scores(context)
```

## File: test_metrics.py
```python
def test_metrics_export_prometheus_text(tmp_path: Path, monkeypatch) -> None
⋮----
governor = GovernorStateStore(tmp_path / "governor.json")
⋮----
crisis = CrisisStateStore(tmp_path / "crisis.json")
⋮----
snapshot = collect_metrics(
text = prometheus_text(snapshot)
⋮----
def test_metrics_include_model_lifecycle_counters(tmp_path: Path, monkeypatch) -> None
⋮----
lifecycle = LifecycleEventLog(tmp_path / "lifecycle.jsonl")
⋮----
quarantine = ModelQuarantineStore(tmp_path / "quarantine.json")
⋮----
def test_metrics_include_recovery_observability(tmp_path: Path, monkeypatch) -> None
```

## File: test_model_blend.py
```python
def test_blend_prefers_higher_quality_model() -> None
⋮----
long = Prediction(1, 0.8, {-1: 0.1, 0: 0.1, 1: 0.8})
short = Prediction(-1, 0.8, {-1: 0.8, 0: 0.1, 1: 0.1})
⋮----
blended = blend_predictions(
```

## File: test_model_codec.py
```python
def test_model_codec_round_trip() -> None
⋮----
blob = serialize_model(RiverDirectionModel())
restored = deserialize_model(blob)
⋮----
research = RiverMulticlassDirectionModel()
research_blob = serialize_research_model(research)
research_restored = deserialize_research_model(research_blob)
⋮----
def test_model_codec_rejects_corrupt_payload() -> None
⋮----
research_blob = serialize_research_model(RiverMulticlassDirectionModel())
⋮----
def test_model_codec_rejects_unknown_version() -> None
```

## File: test_model_quality.py
```python
def test_model_quality_rewards_better_predictions() -> None
⋮----
labels = pd.Series([1, 1, -1, 0, 1, -1, 1, 0, -1, 1])
good = evaluate_model_quality(
bad = evaluate_model_quality(
```

## File: test_model_quarantine.py
```python
def test_quarantine_backoff_grows_after_failures(tmp_path: Path) -> None
⋮----
store = ModelQuarantineStore(tmp_path / "quarantine.json")
policy = QuarantinePolicy(
⋮----
first = store.record_failure(
second = store.record_failure(
⋮----
def test_quarantine_blocks_version_after_threshold(tmp_path: Path) -> None
⋮----
record = store.record_failure(
⋮----
released = store.release("v2")
⋮----
def test_success_resets_failure_history(tmp_path: Path) -> None
⋮----
record = store.record_success("v2")
```

## File: test_mtf_parameter_benchmark.py
```python
def sample_market(n: int = 3200, phase: float = 0.0) -> pd.DataFrame
⋮----
idx = pd.date_range("2026-01-01", periods=n, freq="5min")
t = np.arange(n, dtype=float)
close = (
open_ = close * (1.0 + 0.0004 * np.sin(t / 9.0 + phase))
⋮----
def test_market_benchmark_is_purged_and_reports_directional_evidence() -> None
⋮----
config = MTFBenchmarkConfig(
⋮----
result = evaluate_market_config(
⋮----
def test_parameter_benchmark_ranks_configs_across_markets() -> None
⋮----
markets = {
configs = (
⋮----
results = run_parameter_benchmark(
⋮----
def test_benchmark_payload_is_reproducible_and_explicit() -> None
⋮----
markets = {"A": sample_market()}
configs = (MTFBenchmarkConfig(3, 0.001, 0.25, 600, 0.56),)
⋮----
payload = benchmark_payload(results)
⋮----
def test_btc_focused_grid_is_bounded_and_longer_horizon() -> None
⋮----
grid = btc_focused_benchmark_grid()
⋮----
def test_market_selections_choose_gate_passing_config_per_symbol() -> None
⋮----
selections = market_selections(results)
⋮----
def test_payload_exposes_per_market_selection() -> None
⋮----
configs = (MTFBenchmarkConfig(3, 0.0005, 0.25, 700, 0.50),)
⋮----
def test_parameter_grid_uses_same_random_seed_for_every_config(monkeypatch) -> None
⋮----
seen_random_states: list[int] = []
```

## File: test_mtf_shadow_challenger.py
```python
def sample_market(n: int = 2600) -> pd.DataFrame
⋮----
idx = pd.date_range("2026-01-01", periods=n, freq="5min")
t = np.arange(n, dtype=float)
close = 100.0 + 0.015 * t + 1.3 * np.sin(t / 17.0)
open_ = close * (1.0 + 0.0004 * np.sin(t / 9.0))
⋮----
def test_select_observable_execution_target_delays_three_bar_horizon() -> None
⋮----
market = sample_market(200)
eligible = tuple(market.index[40:])
current = eligible[-1]
⋮----
target = select_observable_execution_target(
⋮----
def test_mtf_shadow_purges_future_labels_and_caps_training(monkeypatch) -> None
⋮----
market = sample_market()
authoritative = make_features(market)
execution_idx = market.index[-4]
captured: dict[str, object] = {}
original_feature_builder = mtf_module.make_multi_timeframe_challenger_features
⋮----
def recording_feature_builder(frame: pd.DataFrame) -> pd.DataFrame
⋮----
class RecordingEnsemble
⋮----
def fit(self, x: pd.DataFrame, y: pd.Series) -> None
⋮----
def predict_one(self, row: pd.Series, regime) -> Prediction
⋮----
result = evaluate_multi_timeframe_shadow(
⋮----
train_index = captured["train_index"]
⋮----
signal_pos = int(market.index.get_loc(execution_idx)) - 1
⋮----
def test_mtf_shadow_rejects_invalid_feature_warmup() -> None
⋮----
market = sample_market(800)
⋮----
def test_mtf_shadow_confidence_gate_turns_weak_direction_flat(monkeypatch) -> None
⋮----
class WeakDirectionalEnsemble
⋮----
def __init__(self, **kwargs) -> None
⋮----
def test_mtf_shadow_rejects_invalid_confidence_gate() -> None
```

## File: test_mtf_shadow_config.py
```python
def test_gold_uses_validated_45m_candidate() -> None
⋮----
config = validated_mtf_shadow_config("GC=F")
⋮----
def test_dax_uses_validated_45m_candidate() -> None
⋮----
config = validated_mtf_shadow_config("^GDAXI")
⋮----
def test_btc_uses_validated_90m_candidate() -> None
⋮----
config = validated_mtf_shadow_config("BTC-USD")
```

## File: test_mtf_shadow_quality.py
```python
def river_payload(execution_time: str, side: int, confidence: float) -> dict[str, object]
⋮----
def test_mtf_quality_joins_river_prediction_by_delayed_execution_time() -> None
⋮----
payloads = [
⋮----
comparison = compare_mtf_shadow_audit_payloads(payloads)
⋮----
def test_mtf_quality_deduplicates_same_evaluated_execution() -> None
⋮----
def test_mtf_quality_exposes_flat_only_evidence() -> None
⋮----
def test_mtf_quality_filters_evidence_by_candidate_version() -> None
⋮----
comparison = compare_mtf_shadow_audit_payloads(
```

## File: test_multi_market.py
```python
TEST_MARKET_NOW = datetime(2026, 9, 21, 12, 0, tzinfo=UTC)
⋮----
@dataclass
class FakeMultiPersistence
⋮----
equities: dict[str, float]
⋮----
def load_runtime(self, runtime_key: str, starting_cash: float) -> PersistedRuntime
⋮----
symbol = runtime_key.split(":", 2)[1]
equity = self.equities[symbol]
⋮----
def load_runtime_status(self, runtime_key: str) -> HostedRuntimeStatus
⋮----
def list_burnin_snapshots(self, runtime_key: str)
⋮----
def list_regimes(self, runtime_key: str)
⋮----
def list_trades(self, runtime_key: str | None = None, *, limit: int | None = None)
⋮----
def load_trade_performance(self, runtime_key: str)
⋮----
def test_configured_markets_default_to_full_bundle(monkeypatch) -> None
⋮----
markets = configured_markets_from_env()
⋮----
def test_configured_default_bundle_uses_34_33_33(monkeypatch) -> None
⋮----
def test_configured_markets_preserve_known_and_custom_labels(monkeypatch) -> None
⋮----
def test_multi_market_cycle_isolates_one_market_failure(monkeypatch, capsys) -> None
⋮----
calls: list[tuple[str, str]] = []
⋮----
def fake_cycle(settings, *, persistence=None, **kwargs)
⋮----
result = run_multi_market_paper_cycle(
⋮----
log_output = capsys.readouterr().out
⋮----
def test_multi_market_overview_scales_normalized_sleeves_to_100k() -> None
⋮----
backend = FakeMultiPersistence(
⋮----
snapshot = build_multi_market_overview(
⋮----
def test_dashboard_renders_multi_market_cards(tmp_path, monkeypatch) -> None
⋮----
page = render_dashboard(
⋮----
# Market PnL is computed on normalized 100k runtimes, so the displayed
# sleeve value MUST be allocation-scaled rather than showing 3x PnL.
⋮----
populated = render_dashboard(
⋮----
expected = f'<small>Realized net · sleeve</small><strong>{allocated_net:.2f}</strong>'
⋮----
def test_multi_market_overview_parallelizes_read_only_observers(monkeypatch) -> None
⋮----
barrier = Barrier(len(DEFAULT_MARKETS))
original = multi_market_module.build_operational_overview
⋮----
def concurrent_observer(persistence, runtime_key, starting_cash)
⋮----
def test_multi_market_cycle_runs_markets_concurrently(monkeypatch) -> None
⋮----
def test_multi_market_overview_marks_stale_heartbeat_as_delayed() -> None
⋮----
original = backend.load_runtime_status
⋮----
def stale_status(runtime_key: str) -> HostedRuntimeStatus
⋮----
status = original(runtime_key)
⋮----
backend.load_runtime_status = stale_status  # type: ignore[method-assign]
⋮----
def test_market_spec_rejects_invalid_fields(spec) -> None
⋮----
def test_multi_market_cycle_rejects_duplicate_symbols(monkeypatch) -> None
⋮----
markets = (
⋮----
def test_multi_market_cycle_rejects_invalid_allocation_sum() -> None
⋮----
def test_multi_market_overview_marks_portfolio_totals_unknown_on_market_error() -> None
⋮----
dax = next(row for row in snapshot["markets"] if row["symbol"] == "^GDAXI")
⋮----
def test_multi_market_cycle_isolates_unexpected_market_exception(monkeypatch) -> None
⋮----
def test_multi_market_cycle_sanitizes_all_unexpected_failures(monkeypatch) -> None
⋮----
failure_by_market = dict(
⋮----
def fake_cycle(settings, *, persistence=None)
```

## File: test_multi_period_promotion.py
```python
def metric(total_return: float, sharpe: float, drawdown: float) -> PerformanceMetrics
⋮----
def test_multi_period_promotion_requires_consistency() -> None
⋮----
champion = [metric(0.10, 0.8, 0.08) for _ in range(5)]
challenger = [
decision = evaluate_multi_period_challenger(
⋮----
def test_multi_period_promotion_rejects_invalid_strong_period_evidence() -> None
⋮----
challenger = [metric(0.15, 1.1, 0.08) for _ in range(5)]
⋮----
decision = evaluate_multi_period_challenger(champion, challenger)
```

## File: test_multi_timeframe_features.py
```python
def sample_market(n: int = 2600) -> pd.DataFrame
⋮----
idx = pd.date_range("2026-01-01", periods=n, freq="5min")
t = np.arange(n, dtype=float)
close = 100.0 + 0.01 * t + 1.8 * np.sin(t / 19.0)
open_ = close * (1.0 + 0.0003 * np.sin(t / 7.0))
⋮----
def test_multi_timeframe_features_include_true_contexts() -> None
⋮----
features = make_multi_timeframe_challenger_features(sample_market())
⋮----
def test_multi_timeframe_features_do_not_change_when_future_prices_change() -> None
⋮----
market = sample_market()
probe_time = market.index[1800]
before = make_multi_timeframe_challenger_features(market).loc[probe_time]
⋮----
altered = market.copy()
future = altered.index > probe_time
⋮----
after = make_multi_timeframe_challenger_features(altered).loc[probe_time]
⋮----
def test_adaptive_labels_use_15_minute_horizon_and_valid_classes() -> None
⋮----
labels = make_volatility_adaptive_labels(
threshold = adaptive_return_threshold(
```

## File: test_multiasset_backtest.py
```python
def market(seed: int, n: int = 420) -> pd.DataFrame
⋮----
rng = np.random.default_rng(seed)
idx = pd.date_range("2022-01-01", periods=n, freq="D")
rets = rng.normal(0.0002, 0.01, n)
close = 100.0 * np.cumprod(1.0 + rets)
open_ = close * (1.0 + rng.normal(0.0, 0.001, n))
⋮----
def test_multiasset_walk_forward_produces_portfolio_curve() -> None
⋮----
backtester = MultiAssetWalkForwardBacktester(
report = backtester.run(
⋮----
def test_multiasset_backtest_annualizes_from_actual_timestamps() -> None
⋮----
report = MultiAssetWalkForwardBacktester(
⋮----
periods = infer_periods_per_year(report.equity_curve.index)
expected = compute_metrics(report.equity_curve, periods)
⋮----
def test_multiasset_backtest_uses_symbol_specific_execution_costs(monkeypatch) -> None
⋮----
seen: list[tuple[str, float, float]] = []
real_config = backtest_module.risk_config_for_symbol
⋮----
def capture(symbol: str, base: RiskConfig)
⋮----
config = real_config(
```

## File: test_multiasset_checkpoint_consistency.py
```python
def _state(step: int) -> MultiAssetState
⋮----
directory = store.root / f"step-{directory_step:012d}"
⋮----
state_path = directory / "state.json"
⋮----
model_path = directory / "A.joblib"
⋮----
manifest = {
⋮----
store = MultiAssetCheckpointStore(tmp_path / "checkpoint")
⋮----
loaded = store.load()
⋮----
generation = store.commit(_state(5), {"A": {"learned": 5}})
manifest_path = store.root / generation / "manifest.json"
manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
```

## File: test_multiasset_checkpoint_manifest_binding.py
```python
def _state(step: int) -> MultiAssetState
⋮----
store = MultiAssetCheckpointStore(tmp_path / "checkpoint")
generation = store.commit(
manifest_path = store.root / generation / "manifest.json"
manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
⋮----
# Build a complete generation through the normal writer, then restore CURRENT
# to simulate a crash immediately before publication of the newer generation.
⋮----
generation = "step-000000000002"
⋮----
loaded = store.load()
```

## File: test_multiasset_checkpoint_orphan_corruption.py
```python
def _state(step: int) -> MultiAssetState
⋮----
def test_checkpoint_ignores_truncated_newer_unpublished_model(tmp_path: Path) -> None
⋮----
store = MultiAssetCheckpointStore(tmp_path / "checkpoint")
⋮----
orphan = store.root / "step-000000000004"
⋮----
state_path = orphan / "state.json"
⋮----
model_path = orphan / "model.joblib"
⋮----
manifest = {
⋮----
loaded = store.load()
```

## File: test_multiasset_checkpoint.py
```python
def state(step: int) -> MultiAssetState
⋮----
def test_checkpoint_round_trip_state_and_models(tmp_path: Path) -> None
⋮----
store = MultiAssetCheckpointStore(tmp_path / "checkpoint")
generation = store.commit(state(7), {"A": {"learned": 7}})
⋮----
loaded = store.load()
⋮----
unpublished = store.root / "step-000000000004"
⋮----
def test_checkpoint_fails_closed_on_corrupted_state(tmp_path: Path) -> None
⋮----
generation = store.commit(state(9), {"A": {"learned": 9}})
⋮----
def test_checkpoint_refuses_to_overwrite_published_generation(tmp_path: Path) -> None
⋮----
store = MultiAssetCheckpointStore(
⋮----
generations = sorted(
⋮----
def test_checkpoint_retention_must_be_positive(tmp_path: Path) -> None
⋮----
orphan = store.root / "step-000000000002"
⋮----
orphan_state = state(2)
state_path = orphan / "state.json"
⋮----
model_path = orphan / store._model_filename("A")
⋮----
manifest = {
⋮----
broken = store.root / "step-000000000004"
⋮----
def test_checkpoint_ignores_corrupt_compressed_unpublished_model(tmp_path: Path) -> None
⋮----
orphan = store.root / "step-000000000004"
⋮----
def test_checkpoint_rejects_pointer_path_traversal(tmp_path: Path) -> None
⋮----
generation = store.current_path.read_text(encoding="utf-8")
manifest = json.loads(
files = [metadata["file"] for metadata in manifest["models"].values()]
⋮----
def test_checkpoint_rejects_manifest_state_path_escape(tmp_path: Path) -> None
⋮----
manifest_path = store.root / generation / "manifest.json"
manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
⋮----
def test_checkpoint_rejects_manifest_model_path_escape(tmp_path: Path) -> None
⋮----
store = MultiAssetCheckpointStore(tmp_path / "checkpoint", retain_generations=1)
⋮----
def fail_prune(*, current: str) -> None
⋮----
generation = store.commit(state(2), {"A": {"learned": 2}})
⋮----
newer = store._generation_dir("step-000000000002")
staged = store.root / ".step-000000000002.tmp"
⋮----
state_path = staged / "state.json"
⋮----
model_path = staged / store._model_filename("A")
⋮----
file_calls: list[str] = []
directory_calls: list[str] = []
⋮----
generation = store.commit(state(8), {"A": {"learned": 8}})
⋮----
stale = store.root / ".step-000000000009.existing.tmp"
⋮----
marker = stale / "marker"
```

## File: test_multiasset_evolution.py
```python
def market(seed: int, n: int = 360) -> pd.DataFrame
⋮----
rng = np.random.default_rng(seed)
idx = pd.date_range("2023-01-01", periods=n, freq="D")
t = np.arange(n, dtype=float)
noise = rng.normal(0.0, 0.3, n)
close = 100 + 0.04 * t + 3.0 * np.sin(t / (7.0 + seed)) + noise
open_ = close * (1.0 + 0.001 * np.sin(t / (4.0 + seed)))
⋮----
def test_multiasset_evolution_runs_with_global_generation_store(tmp_path) -> None
⋮----
pool = ExpertPoolStore(tmp_path / "pool.json")
generations = GenerationStore(
⋮----
result = run_multiasset_evolution_cycle(
```

## File: test_multiasset_market_context.py
```python
def market(seed: int, n: int = 120, *, offset_minutes: int = 0) -> pd.DataFrame
⋮----
rng = np.random.default_rng(seed)
index = pd.date_range(
returns = rng.normal(0.0003, 0.01, n)
close = 100.0 * np.cumprod(1.0 + returns)
open_ = close * (1.0 + rng.normal(0.0, 0.001, n))
⋮----
def test_prepare_multiasset_market_context_builds_aligned_inputs() -> None
⋮----
markets = {"A": market(1), "B": market(2)}
⋮----
context = prepare_multiasset_market_context(markets, ModelConfig())
⋮----
def test_prepare_multiasset_market_context_rejects_unaligned_latest_bar() -> None
⋮----
def test_prepare_multiasset_market_context_rejects_insufficient_assets() -> None
⋮----
def test_prepare_multiasset_market_context_rejects_short_history() -> None
⋮----
def test_prepare_multiasset_market_context_rejects_missing_columns() -> None
⋮----
broken = market(1).drop(columns=["Volume"])
⋮----
broken = market(1)
```

## File: test_multiasset_runtime.py
```python
def market(seed: int, n: int = 120) -> pd.DataFrame
⋮----
rng = np.random.default_rng(seed)
idx = pd.date_range("2025-01-01", periods=n, freq="D")
rets = rng.normal(0.0003, 0.01, n)
close = 100.0 * np.cumprod(1.0 + rets)
open_ = close * (1.0 + rng.normal(0.0, 0.001, n))
⋮----
def test_multiasset_runtime_is_persistent_and_idempotent(tmp_path: Path) -> None
⋮----
runtime = MultiAssetPaperRuntime(
markets = {"A": market(1), "B": market(2)}
⋮----
first = runtime.step(markets)
second = runtime.step(markets)
⋮----
records = [
step_record = next(record for record in records if record["event"] == "multiasset_runtime_step")
intelligence = step_record["payload"]["intelligence"]
⋮----
drift_store = DriftRetrainStore(tmp_path / "drift_retrain.json")
⋮----
def fail_batch_retrain(*_args, **_kwargs)
⋮----
markets = {"A": market(11, n=180), "B": market(12, n=180)}
result = runtime.step(markets)
⋮----
state_store = MultiAssetStateStore(tmp_path / "state.json")
⋮----
def fail_state_save(_state) -> None
⋮----
markets = {"A": market(31), "B": market(32)}
⋮----
legacy = json.loads((tmp_path / "state.json").read_text(encoding="utf-8"))
⋮----
requested_symbols: list[str] = []
observed_costs: list[tuple[float, float]] = []
⋮----
def fake_symbol_config(symbol: str, base: RiskConfig) -> RiskConfig
⋮----
def capture_fill(**kwargs)
⋮----
result = runtime.step({"A": market(41), "B": market(42)})
⋮----
allocation_store = AllocationStateStore(tmp_path / "allocation.json")
crisis_store = CrisisStateStore(tmp_path / "crisis.json")
resilience_store = ResilienceStateStore(tmp_path / "resilience.json")
governor_store = GovernorStateStore(tmp_path / "governor.json")
⋮----
def fail_checkpoint(*_args, **_kwargs) -> None
⋮----
quality_store = QualityStore(tmp_path / "quality.json")
meta_store = MetaRouterStore(tmp_path / "meta.json")
economic_store = EconomicMetaStore(tmp_path / "economic.json")
lifecycle_log = LifecycleEventLog(tmp_path / "lifecycle.jsonl")
drift_store = DriftRetrainStore(tmp_path / "drift.json")
⋮----
def test_multiasset_model_paths_are_collision_resistant(tmp_path: Path) -> None
⋮----
symbols = ("GC=F", "GC/F", "^GC_F")
⋮----
def test_multiasset_online_model_legacy_path_is_migrated(tmp_path: Path) -> None
⋮----
symbol = "GC=F"
legacy_path = runtime._legacy_model_path(symbol)
⋮----
expected = RiverDirectionModel()
⋮----
loaded = runtime._load_model(symbol)
⋮----
features = pd.DataFrame(index=pd.date_range("2025-01-01", periods=2))
labels = pd.Series(index=features.index, dtype=float)
signal_idx = features.index[-1]
⋮----
legacy_batch = runtime._legacy_batch_model_path(symbol)
⋮----
legacy_specialist = runtime._legacy_specialist_path(symbol, "trend")
⋮----
batch = runtime._load_or_train_batch_model(
specialist = runtime._load_or_train_specialist(
⋮----
checkpoint_store = MultiAssetCheckpointStore(tmp_path / "checkpoint")
⋮----
def fail_legacy_load(symbol: str)
⋮----
result = runtime.step({"A": market(71), "B": market(72)})
⋮----
def test_multiasset_rejects_invalid_model_artifact_types(tmp_path: Path) -> None
⋮----
online_path = runtime._model_path(symbol)
⋮----
batch_path = runtime._batch_model_path(symbol)
⋮----
specialist_path = runtime._specialist_path(symbol, "trend")
```

## File: test_multiasset_scheduler.py
```python
def market(seed: int, n: int = 120) -> pd.DataFrame
⋮----
rng = np.random.default_rng(seed)
idx = pd.date_range("2025-01-01", periods=n, freq="D")
close = 100.0 * np.cumprod(1.0 + rng.normal(0.0002, 0.01, n))
⋮----
def test_multiasset_scheduler_refuses_to_run_when_halted(tmp_path: Path) -> None
⋮----
governor = GovernorStateStore(tmp_path / "governor.json")
⋮----
runtime = MultiAssetPaperRuntime(
scheduler = MultiAssetPaperScheduler(
```

## File: test_multiasset_state.py
```python
def test_multiasset_state_round_trip(tmp_path: Path) -> None
⋮----
store = MultiAssetStateStore(tmp_path / "state.json")
state = MultiAssetState(
⋮----
loaded = store.load(100_000.0)
```

## File: test_online.py
```python
def row(value: float) -> pd.Series
⋮----
def test_river_model_learns_incrementally() -> None
⋮----
model = RiverDirectionModel()
⋮----
label = 1 if value > 0.2 else (-1 if value < -0.2 else 0)
⋮----
prediction = model.predict_one(row(0.9))
⋮----
def test_research_river_multiclass_learns_all_three_directions() -> None
⋮----
model = RiverMulticlassDirectionModel()
⋮----
label = -1 if value < -0.7 else (1 if value > 0.7 else 0)
⋮----
short = model.predict_one(row(-2.0))
long = model.predict_one(row(2.0))
⋮----
# The research state survives a v2-only round trip after actual learning.
⋮----
restored = deserialize_research_model(serialize_research_model(model))
⋮----
def test_legacy_river_binary_probabilities_do_not_include_short() -> None
⋮----
# Document existing v1 limitation without silently changing stored models.
⋮----
label = -1 if value < -0.2 else (1 if value > 0.2 else 0)
⋮----
negative = model.predict_one(row(-0.9))
```

## File: test_orchestrator_trigger.py
```python
def test_orchestrator_configuration_accepts_injected_runtime(tmp_path: Path) -> None
⋮----
runtime = PaperAutonomousRuntime(
orchestrator = AutonomousPaperOrchestrator(
```

## File: test_paper_cycle_cli.py
```python
runner = CliRunner()
⋮----
def test_cli_calls_shared_production_service(monkeypatch) -> None
⋮----
seen: list[ProductionPaperCycleSettings] = []
⋮----
def fake_service(settings: ProductionPaperCycleSettings) -> PaperCycleResult
⋮----
result = runner.invoke(
⋮----
def test_cli_sanitizes_shared_service_failure(monkeypatch) -> None
⋮----
def fail(settings: ProductionPaperCycleSettings) -> PaperCycleResult
⋮----
result = runner.invoke(command_app.app, ["paper-cycle"])
```

## File: test_paper_cycle_materialized_fresh.py
```python
def sample_market(n: int = 110) -> pd.DataFrame
⋮----
idx = pd.date_range("2025-01-01", periods=n, freq="5min")
t = np.arange(n, dtype=float)
close = 100.0 + 0.1 * t + 2.0 * np.sin(t / 5.0)
open_ = close * (1.0 + 0.001 * np.sin(t / 3.0))
⋮----
def test_materialized_empty_runtime_is_treated_as_fresh(tmp_path: Path) -> None
⋮----
backend = FilePaperPersistence(tmp_path)
⋮----
market = sample_market()
⋮----
def runtime_factory(**kwargs) -> PaperAutonomousRuntime
⋮----
runtime = runtime_factory(
eligible = runtime._eligible_execution_indices(market)
runner = PaperCycleRunner(
⋮----
result = runner.run_once(
```

## File: test_paper_cycle_postgres.py
```python
def sample_market(n: int) -> pd.DataFrame
⋮----
idx = pd.date_range("2025-01-01", periods=n, freq="5min")
t = np.arange(n, dtype=float)
close = 100.0 + 0.1 * t + 2.0 * np.sin(t / 5.0)
open_ = close * (1.0 + 0.001 * np.sin(t / 3.0))
⋮----
def runtime_factory(lock_path: Path)
⋮----
def build(**kwargs) -> PaperAutonomousRuntime
⋮----
def test_paper_cycle_survives_postgres_object_reconstruction(tmp_path: Path) -> None
⋮----
database_url = os.environ["TEST_DATABASE_URL"]
symbol = f"PAPER-CYCLE-{uuid4().hex[:8]}"
interval = "5m"
runtime_key = build_runtime_key(symbol, interval)
first_market = sample_market(105)
second_market = sample_market(110)
⋮----
first_persistence = PostgresPaperPersistence(database_url)
⋮----
first_runner = PaperCycleRunner(
⋮----
first_result = first_runner.run_once(
first_snapshot = first_persistence.load_runtime(runtime_key, 100_000.0)
⋮----
second_persistence = PostgresPaperPersistence(database_url)
⋮----
second_runner = PaperCycleRunner(
eligibility_runtime = runtime_factory(tmp_path / "eligibility.lock")(
expected_latest = eligibility_runtime._eligible_execution_indices(second_market)[-1]
⋮----
second_result = second_runner.run_once(
final = second_persistence.load_runtime(runtime_key, 100_000.0)
```

## File: test_paper_cycle_service.py
```python
class FakePersistence
⋮----
def __init__(self, *, initial_status: HostedRuntimeStatus | None = None) -> None
⋮----
def save_runtime_status(self, runtime_key: str, status: HostedRuntimeStatus) -> None
⋮----
def load_runtime_status(self, runtime_key: str) -> HostedRuntimeStatus | None
⋮----
def load_runtime(self, runtime_key: str, starting_cash: float) -> PersistedRuntime
⋮----
class FakeRunner
⋮----
def __init__(self, persistence: FakePersistence) -> None
⋮----
def test_service_persists_starting_and_running_status() -> None
⋮----
backend = FakePersistence()
result = run_production_paper_cycle(
⋮----
final = backend.statuses[-1]
⋮----
def test_persistence_factory_failure_is_sanitized() -> None
⋮----
def broken_factory()
⋮----
error = caught.value
⋮----
def test_starting_status_failure_never_runs_worker() -> None
⋮----
calls = 0
⋮----
def broken_save(runtime_key, status)
⋮----
def runner_factory(persistence)
⋮----
def test_worker_failure_writes_sanitized_error_status() -> None
⋮----
class BrokenRunner
⋮----
def run_once(self, **kwargs)
⋮----
def test_error_status_failure_does_not_mask_worker_failure() -> None
⋮----
original_save = backend.save_runtime_status
writes = 0
⋮----
def flaky_save(runtime_key, status)
⋮----
def test_success_resets_consecutive_cycle_errors() -> None
⋮----
backend = FakePersistence(
⋮----
def test_failure_increments_consecutive_cycle_errors() -> None
⋮----
def test_service_propagates_shadow_challenger_when_enabled() -> None
⋮----
runner = FakeRunner(backend)
⋮----
def test_service_propagates_separate_mtf_period() -> None
⋮----
def test_known_runtime_failure_writes_safe_diagnostic_code() -> None
⋮----
def test_unknown_runtime_failure_stays_sanitized() -> None
⋮----
def test_market_data_quality_failure_writes_safe_diagnostic_code() -> None
⋮----
def test_no_new_bar_keeps_last_completed_paper_decision() -> None
⋮----
last_processed = "2026-09-16 08:00:00+00:00"
⋮----
class NoNewBarRunner
⋮----
# Repeated scheduler polls do not manufacture a fresh prediction.
recent = paper_signal_snapshot(
⋮----
expired = paper_signal_snapshot(
⋮----
completed = backend.statuses[-1]
```

## File: test_paper_cycle_workflow.py
```python
WORKFLOW_PATH = Path(".github/workflows/paper-cycle.yml")
WORKER_CONFIG_PATH = Path("infra/cloudflare-paper-scheduler/wrangler.toml")
⋮----
class FakeResponse
⋮----
status = 200
⋮----
def __init__(self, payload: dict[str, object], *, status: int = 200) -> None
⋮----
def __enter__(self)
⋮----
def __exit__(self, *_args)
⋮----
def read(self, size: int) -> bytes
⋮----
def test_paper_cycle_workflow_uses_authenticated_render_not_expired_db() -> None
⋮----
text = WORKFLOW_PATH.read_text(encoding="utf-8")
worker = WORKER_CONFIG_PATH.read_text(encoding="utf-8")
required = (
⋮----
seen = []
⋮----
def fake_open(request, timeout)
⋮----
outcome = run_fallback("https://example.invalid", "server-secret", opener=fake_open)
⋮----
calls = []
⋮----
def test_fallback_runs_after_scheduler_telemetry_failure() -> None
⋮----
def test_fallback_rejects_missing_token_without_network() -> None
⋮----
def test_fallback_reports_sanitized_http_failure() -> None
⋮----
def test_fallback_fails_closed_when_paper_cycle_has_partial_market_failure() -> None
⋮----
def test_fallback_rejects_malformed_and_future_scheduler_ages() -> None
```

## File: test_paper_cycle.py
```python
def sample_market(n: int = 110) -> pd.DataFrame
⋮----
idx = pd.date_range("2025-01-01", periods=n, freq="5min")
t = np.arange(n, dtype=float)
close = 100.0 + 0.1 * t + 2.0 * np.sin(t / 5.0)
open_ = close * (1.0 + 0.001 * np.sin(t / 3.0))
⋮----
def runtime_factory(tmp_path: Path)
⋮----
def build(**kwargs) -> PaperAutonomousRuntime
⋮----
runtime = runtime_factory(tmp_path)(
⋮----
def test_fresh_runtime_processes_only_latest_eligible_bar(tmp_path: Path) -> None
⋮----
backend = FilePaperPersistence(tmp_path)
df = sample_market()
⋮----
runner = build_runner(tmp_path, backend, df)
⋮----
result = runner.run_once(
state = backend.load_runtime(runtime.runtime_key, 100_000.0).state
⋮----
audit = json.loads(backend.audit_log.path.read_text(encoding="utf-8").splitlines()[-1])
⋮----
def test_existing_runtime_catches_up_oldest_first(tmp_path: Path) -> None
⋮----
audit_rows = [
catchup_times = [row["payload"]["execution_time"] for row in audit_rows[1:]]
⋮----
def test_catchup_cap_leaves_remaining_backlog(tmp_path: Path) -> None
⋮----
calls = {"features": 0, "labels": 0}
original_make_features = runtime_module.make_features
original_make_labels = runtime_module.make_labels
⋮----
def counted_make_features(market)
⋮----
def counted_make_labels(market, *, horizon_bars, return_threshold)
⋮----
def test_missing_last_processed_in_history_fails_closed(tmp_path: Path) -> None
⋮----
runner = build_runner(tmp_path, backend, sample_market())
⋮----
def test_no_new_bar_is_healthy_and_idempotent(tmp_path: Path) -> None
⋮----
def test_max_catchup_bars_must_be_positive(tmp_path: Path) -> None
⋮----
def test_revision_conflict_reloads_and_continues(tmp_path: Path) -> None
⋮----
primary = runtime_factory(tmp_path)(
competitor = runtime_factory(tmp_path)(
conflict_target: list[object] = []
⋮----
class ConflictOnceRuntime
⋮----
risk_config = primary.risk_config
⋮----
def prepare_market(self, market)
⋮----
def step_prepared(self, prepared, target)
⋮----
state = backend.load_runtime(primary.runtime_key, 100_000.0).state
⋮----
runner = build_runner(
⋮----
final = backend.load_runtime(primary.runtime_key, 100_000.0).state
⋮----
target = eligible[-1]
signal = df.index[int(df.index.get_loc(target)) - 1]
train_end = df.index[int(df.index.get_loc(signal)) - 1]
calls: list[object] = []
⋮----
# Exercise opt-in audit attachment without allowing the observer
# to change the authoritative River-v1 decision.
⋮----
payload = audit_rows[-1]["payload"]
⋮----
df = sample_market(109)
⋮----
current_target = eligible[-1]
mtf_target = eligible[-3]
mtf_signal = df.index[int(df.index.get_loc(mtf_target)) - 1]
⋮----
primary = sample_market(217)
long_history = sample_market(900)
calls: list[str] = []
seen_rows: list[int] = []
⋮----
def loader(symbol: str, period: str, interval: str) -> pd.DataFrame
⋮----
def fake_mtf(market, authoritative_features, execution_idx, **kwargs)
⋮----
runner = PaperCycleRunner(
⋮----
def test_mtf_boundary_aligns_with_candidate_horizon() -> None
⋮----
primary = sample_market(110)
⋮----
long_history = sample_market(1400)
captured: dict[str, object] = {}
⋮----
long_history = sample_market(1600)
⋮----
def test_pending_targets_resume_when_last_processed_is_raw_market_bar() -> None
⋮----
market = sample_market(120)
eligible = tuple(market.index[40:])
state = RuntimeState(
snapshot = PersistedRuntime(
⋮----
pending = PaperCycleRunner._pending_targets(
⋮----
def test_pending_targets_still_fail_when_persisted_bar_is_not_loaded() -> None
⋮----
def test_pending_targets_resume_when_provider_removed_persisted_bar() -> None
⋮----
missing_bar = market.index[60]
provider_index = market.index.delete(60)
⋮----
def test_pending_targets_allow_bounded_gap_before_loaded_history() -> None
⋮----
persisted = market.index[0] - pd.Timedelta(days=2)
⋮----
def test_pending_targets_reject_gap_beyond_three_days() -> None
⋮----
persisted = market.index[0] - pd.Timedelta(days=4)
⋮----
df = sample_market(120)
df = df.drop(index=df.index[10:110:10])
⋮----
df = sample_market(220)
df = df.drop(index=df.index[150])
# The provider can include the current, unfinished five-minute candle.
# Freeze the clock to prove the authoritative paper step discards it.
now = pd.Timestamp("2026-10-21T12:02:00+00:00")
last = df.index[-1].tz_localize("UTC")
⋮----
# A forward River-v2 signal can now use the latest *completed* bar,
# instead of silently skipping a still-forming provider candle.
⋮----
complete = paper_cycle_module._completed_market_bars(df, interval="5m", now=now)
sample = observe_river_v2_forward(
⋮----
recent = long_history.index[-100:]
long_history = long_history.drop(index=recent[10:90:10])
⋮----
mtf_calls = 0
⋮----
def fake_mtf(*args, **kwargs)
⋮----
def test_kronos_research_compares_same_windows_with_river_and_momentum() -> None
⋮----
market = sample_market(330)
config = ResearchConfig(
calls: list[tuple[pd.Timestamp, pd.Timestamp]] = []
⋮----
class FakeKronos
⋮----
def predict(self, **kwargs)
⋮----
history = kwargs["df"]
x_times = kwargs["x_timestamp"]
y_times = kwargs["y_timestamp"]
⋮----
result = evaluate_walk_forward(market, FakeKronos(), config)
summary = result["summary"]
observations = result["observations"]
⋮----
# River needs feature warm-up before 50 *matured* labels can be learned.
# An initial cold-start window must remain FLAT, not fabricate a trade.
⋮----
def test_kronos_river_reference_never_trains_on_unmatured_labels(monkeypatch) -> None
⋮----
model_instances = []
⋮----
class RecordingRiver
⋮----
def __init__(self)
⋮----
def learn_one(self, row, label)
⋮----
def predict_one(self, row)
⋮----
market = sample_market(290)
⋮----
class FlatKronos
⋮----
report = evaluate_walk_forward(
⋮----
# The instrumented predictor is only called after 50 mature examples.
# Earlier windows must not bypass the research model cold-start guard.
```

## File: test_paper_execution.py
```python
def test_rebalance_fill_handles_signed_target_and_flip() -> None
⋮----
fill = calculate_rebalance_fill(
⋮----
def test_rebalance_fill_flattening_charges_turnover_costs() -> None
⋮----
@pytest.mark.parametrize("price", [0.0, -1.0])
def test_rebalance_fill_rejects_non_positive_prices(price: float) -> None
⋮----
def test_rebalance_fill_rejects_non_finite_inputs(field: str, value: float) -> None
⋮----
kwargs = {
⋮----
def test_rebalance_fill_rejects_negative_execution_costs() -> None
```

## File: test_performance_metrics.py
```python
def _trade(pnl: float) -> TradeSnapshot
⋮----
def test_performance_metrics_empty_history() -> None
⋮----
metrics = calculate_performance_metrics(())
⋮----
def test_performance_metrics_profit_factor_and_average() -> None
⋮----
metrics = calculate_performance_metrics(
⋮----
def test_performance_metrics_max_drawdown_uses_cumulative_realized_pnl() -> None
⋮----
def test_performance_metrics_profit_factor_is_infinite_without_losses() -> None
⋮----
metrics = calculate_performance_metrics((_trade(5.0), _trade(7.0)))
⋮----
def test_performance_payload_marks_unmeasured_history_unavailable() -> None
⋮----
metrics = performance_metrics_from_totals(
⋮----
def test_performance_payload_serializes_infinite_profit_factor_explicitly() -> None
⋮----
payload = performance_payload(metrics)
⋮----
def test_paper_performance_evidence_requires_sample_and_pnl_coverage() -> None
⋮----
def evidence(trades: int, observed: int) -> bool
```

## File: test_performance.py
```python
def test_metrics_for_monotonic_equity() -> None
⋮----
equity = pd.Series(np.linspace(100_000.0, 120_000.0, 253))
metrics = compute_metrics(equity)
⋮----
def test_buy_and_hold_is_normalized_to_starting_equity() -> None
⋮----
prices = pd.Series([100.0, 110.0, 120.0])
curve = buy_and_hold_equity(prices, 100_000.0)
⋮----
def test_infer_periods_per_year_from_elapsed_timestamps() -> None
⋮----
index = pd.date_range("2026-01-01", periods=13, freq="30D", tz="UTC")
periods = infer_periods_per_year(index)
⋮----
# Incomplete or reordered histories must not silently inflate Sharpe
# ratios or transform numeric bar positions into artificial timestamps.
invalid_timelines = (
⋮----
def test_extreme_short_window_annualization_stays_finite() -> None
⋮----
equity = pd.Series([1.0, 1e100])
metrics = compute_metrics(equity, periods_per_year=525_600.0)
⋮----
def test_performance_refuses_incomplete_or_invalid_equity_curves(equity) -> None
⋮----
def test_performance_rejects_nonfinite_returns_from_finite_equity() -> None
⋮----
def test_benchmark_refuses_invalid_price_history(prices) -> None
⋮----
@pytest.mark.parametrize("capital", [np.nan, np.inf, 0.0, -1.0])
def test_benchmark_refuses_invalid_starting_equity(capital) -> None
```

## File: test_persistence_contract.py
```python
def test_build_runtime_key_is_stable() -> None
⋮----
def test_commit_outcome_exposes_conflict() -> None
```

## File: test_persistence_factory.py
```python
def test_factory_uses_file_backend_without_database_url(monkeypatch, tmp_path) -> None
⋮----
persistence = build_paper_persistence(file_root=tmp_path)
⋮----
def test_factory_treats_blank_database_url_as_absent(monkeypatch, tmp_path) -> None
⋮----
def test_factory_uses_postgres_and_initializes_schema(monkeypatch) -> None
⋮----
calls: list[str] = []
⋮----
def fake_initialize(self) -> None
⋮----
persistence = factory.build_paper_persistence()
```

## File: test_persistence.py
```python
def test_model_store_round_trip(tmp_path: Path) -> None
⋮----
store = ModelStore(tmp_path / "models")
model = {"weights": [1, 2, 3]}
saved = store.save("champion", model, {"version": "v1"})
```

## File: test_pnl_attribution.py
```python
def test_pnl_attribution_handles_long_and_short() -> None
⋮----
result = attribute_pnl(
```

## File: test_portfolio_intelligence.py
```python
def sample_returns(n: int = 300) -> pd.DataFrame
⋮----
rng = np.random.default_rng(123)
⋮----
def test_volatility_targeting_scales_weights() -> None
⋮----
returns = sample_returns()
base = pd.Series({"A": 0.4, "B": 0.3, "C": 0.3})
⋮----
def test_drawdown_reduces_leverage() -> None
⋮----
base = pd.Series({"A": 0.5, "B": 0.5, "C": 0.0})
⋮----
def test_low_confidence_asset_is_zeroed() -> None
⋮----
def test_high_correlation_reduces_leverage() -> None
⋮----
x = np.linspace(-0.02, 0.02, 300)
returns = pd.DataFrame(
⋮----
def test_low_correlation_keeps_full_correlation_scale() -> None
⋮----
def test_portfolio_intelligence_fails_closed_on_insufficient_correlation_history() -> None
⋮----
weights = pd.Series({"A": 0.5, "B": 0.5})
returns = pd.DataFrame({"A": [0.01], "B": [0.01]})
⋮----
def test_portfolio_intelligence_sanitizes_nonfinite_confidence() -> None
⋮----
@pytest.mark.parametrize("equity,peak", [(float("nan"), 100_000.0), (100_000.0, 0.0)])
def test_portfolio_intelligence_rejects_invalid_equity(equity: float, peak: float) -> None
⋮----
weights = pd.Series({"A": 1.0})
returns = pd.DataFrame({"A": [0.01, -0.01]})
```

## File: test_portfolio_risk.py
```python
def test_portfolio_risk_rejects_excess_single_asset_exposure() -> None
⋮----
rng = np.random.default_rng(7)
returns = pd.DataFrame(
notionals = pd.Series({"A": 60_000.0, "B": 10_000.0})
report = evaluate_portfolio_risk(
⋮----
def test_portfolio_risk_detects_high_pair_correlation() -> None
⋮----
x = np.linspace(-0.02, 0.02, 200)
returns = pd.DataFrame({"A": x, "B": x * 1.01})
notionals = pd.Series({"A": 20_000.0, "B": 20_000.0})
⋮----
@pytest.mark.parametrize("equity", [math.nan, math.inf, -math.inf, 0.0])
def test_portfolio_risk_rejects_invalid_equity(equity: float) -> None
⋮----
@pytest.mark.parametrize("notional", [math.nan, math.inf, -math.inf])
def test_portfolio_risk_rejects_nonfinite_asset_exposure(notional: float) -> None
⋮----
def test_portfolio_risk_rejects_nonfinite_limits(field: str) -> None
⋮----
def test_portfolio_risk_rejects_undefined_correlation_between_active_assets() -> None
⋮----
returns = pd.DataFrame({"A": [0.01, -0.01, 0.02], "B": [0.0, 0.0, 0.0]})
report = evaluate_portfolio_risk(notionals, 100_000.0, returns)
⋮----
def test_portfolio_risk_rejects_missing_active_asset_history() -> None
⋮----
returns = pd.DataFrame({"A": [0.01, -0.01, 0.02]})
⋮----
def test_portfolio_risk_ignores_missing_history_for_flat_asset() -> None
⋮----
notionals = pd.Series({"A": 20_000.0, "B": 0.0})
```

## File: test_portfolio_selection.py
```python
def test_replacement_requires_portfolio_and_score_improvement() -> None
⋮----
marginal = MarginalAlphaReport(
decision = evaluate_portfolio_replacement(
```

## File: test_portfolio.py
```python
def test_inverse_volatility_weights_are_capped_and_normalized() -> None
⋮----
rng = np.random.default_rng(42)
returns = pd.DataFrame(
weights = inverse_volatility_weights(
⋮----
notionals = target_notionals(100_000.0, weights)
```

## File: test_postgres_persistence.py
```python
DATABASE_URL = os.environ["TEST_DATABASE_URL"]
RUNTIME_KEY = "paper:GC=F:5m:online-river:v1"
BTC_RUNTIME_KEY = "paper:BTC-USD:5m:online-river:v1"
DAX_RUNTIME_KEY = "paper:^GDAXI:5m:online-river:v1"
⋮----
def test_opt_in_postgres_pool_reuses_connection_safely(backend) -> None
⋮----
pooled = PostgresPaperPersistence(DATABASE_URL, pooled=True)
⋮----
pids = []
⋮----
# The free Neon compute must be allowed to sleep between paper cycles.
⋮----
def test_postgres_16_is_reachable() -> None
⋮----
commit_state = state or _state()
⋮----
@pytest.fixture
def backend()
⋮----
persistence = PostgresPaperPersistence(DATABASE_URL)
⋮----
def test_schema_initialization_is_idempotent(backend) -> None
⋮----
def test_runtime_state_and_model_survive_new_instance(backend) -> None
⋮----
fresh = backend.load_runtime(RUNTIME_KEY, 100_000.0)
⋮----
restored = PostgresPaperPersistence(DATABASE_URL).load_runtime(RUNTIME_KEY, 100_000.0)
⋮----
def test_fresh_instances_continue_from_persisted_revision(backend) -> None
⋮----
restarted = PostgresPaperPersistence(DATABASE_URL)
after_restart = restarted.load_runtime(RUNTIME_KEY, 100_000.0)
⋮----
second_state = _state(cash=99_800.0, processed_bars=2)
⋮----
restored_again = PostgresPaperPersistence(DATABASE_URL).load_runtime(
⋮----
def test_same_revision_has_exactly_one_winner(backend) -> None
⋮----
first = _commit(trade=_trade(side="BUY"))
second = _commit(trade=_trade(side="SELL"))
⋮----
restored = backend.load_runtime(RUNTIME_KEY, 100_000.0)
⋮----
trades = backend.list_trades(RUNTIME_KEY)
⋮----
def test_duplicate_logical_trade_is_idempotent_across_revisions(backend) -> None
⋮----
trade = _trade()
⋮----
def test_failure_before_state_commit_rolls_back_everything(backend) -> None
⋮----
def fail() -> None
⋮----
failing = PostgresPaperPersistence(DATABASE_URL, before_state_commit=fail)
⋮----
def test_runtime_status_survives_new_instance(backend) -> None
⋮----
status = HostedRuntimeStatus(
⋮----
restored = PostgresPaperPersistence(DATABASE_URL).load_runtime_status(RUNTIME_KEY)
⋮----
def test_regime_coverage_is_deduplicated_and_persisted(backend) -> None
⋮----
snapshots = backend.list_burnin_snapshots(RUNTIME_KEY)
⋮----
def test_postgres_loads_shadow_quality_from_audit(backend) -> None
⋮----
commit = _commit()
shadow_commit = RuntimeStepCommit(
⋮----
comparison = backend.load_shadow_quality(RUNTIME_KEY)
⋮----
def test_scheduler_deliveries_survive_postgres_restart(backend) -> None
⋮----
delivery = SchedulerDelivery(
⋮----
restored = PostgresPaperPersistence(DATABASE_URL)
⋮----
def test_postgres_persists_pnl_provenance_and_performance_coverage(backend) -> None
⋮----
known = _trade(side="BUY", pnl=5.0, pnl_known=True)
unknown = _trade(side="SELL", pnl=0.0, pnl_known=False)
⋮----
metrics = backend.load_trade_performance(RUNTIME_KEY)
⋮----
def test_trade_event_key_ignores_pnl_provenance_metadata() -> None
⋮----
known = _trade(pnl=0.0, pnl_known=True)
unknown = _trade(pnl=0.0, pnl_known=False)
⋮----
def test_schema_upgrade_adds_pnl_accounting_columns_without_reset(backend) -> None
⋮----
columns = {(row[0], row[1]) for row in cursor.fetchall()}
⋮----
def test_postgres_portfolio_performance_uses_global_trade_chronology(backend) -> None
⋮----
metrics = backend.load_portfolio_trade_performance(
⋮----
def test_postgres_portfolio_performance_empty_runtime_set_is_empty(backend) -> None
⋮----
metrics = backend.load_portfolio_trade_performance(())
```

## File: test_process_watch.py
```python
def test_process_watch_times_out_and_stops_worker() -> None
⋮----
process = subprocess.Popen(
result = wait_with_timeout(process, timeout_seconds=0.05)
```

## File: test_promotion_guard.py
```python
BASELINE = {
⋮----
def test_promotion_guard_accepts_better_challenger() -> None
⋮----
decision = evaluate_promotion(
⋮----
def test_promotion_guard_rejects_drawdown_regression() -> None
⋮----
def test_promotion_guard_is_fail_closed_on_missing_metric() -> None
⋮----
def test_promotion_policy_can_require_strict_score_gain() -> None
```

## File: test_promotion.py
```python
def metrics(total_return: float, sharpe: float, max_drawdown: float) -> PerformanceMetrics
⋮----
def test_promotes_materially_better_challenger() -> None
⋮----
champion = metrics(0.10, 0.8, 0.08)
challenger = metrics(0.14, 1.05, 0.09)
decision = evaluate_challenger(champion, challenger)
⋮----
def test_rejects_excess_drawdown() -> None
⋮----
challenger = metrics(0.20, 1.2, 0.15)
policy = PromotionPolicy(max_drawdown_increase=0.02)
decision = evaluate_challenger(champion, challenger, policy)
⋮----
def test_promotion_rejects_nonfinite_metrics_even_if_relative_checks_would_pass() -> None
⋮----
better = metrics(0.14, 1.05, 0.09)
⋮----
invalid = replace(better, **{field: value})
decision = evaluate_challenger(champion, invalid)
⋮----
def test_promotion_rejects_losing_challenger_outperforming_losing_champion() -> None
⋮----
champion = metrics(-0.20, -2.0, 0.25)
challenger = metrics(-0.05, -0.5, 0.20)
⋮----
def test_promotion_rejects_invalid_drawdown_or_policy() -> None
⋮----
result = evaluate_challenger(champion, replace(better, max_drawdown=-0.1))
```

## File: test_purged_cv.py
```python
def test_purged_cv_separates_train_and_test() -> None
⋮----
index = pd.RangeIndex(0, 400)
folds = purged_expanding_folds(
⋮----
def test_purged_cv_embargo_moves_next_test_forward() -> None
```

## File: test_qualification_guard.py
```python
def test_qualification_guard_requires_matching_scope() -> None
⋮----
record = QualificationRecord(
⋮----
ok = validate_qualification_record(
⋮----
bad = validate_qualification_record(
⋮----
def test_qualification_guard_rejects_low_reliability() -> None
⋮----
reliability = ReliabilityReport(
⋮----
result = validate_qualification_record(
⋮----
def test_qualification_guard_rejects_insufficient_reliability_observation() -> None
```

## File: test_qualification_store.py
```python
def test_qualification_store_round_trip(tmp_path: Path) -> None
⋮----
result = SoakResult(
qualification = evaluate_soak_qualification(result)
store = QualificationStore(tmp_path / "qualification.json")
saved = store.save(result, qualification)
loaded = store.load()
⋮----
def test_qualification_store_persists_reliability_sla(tmp_path: Path) -> None
⋮----
reliability = ReliabilityReport(
⋮----
saved = store.save(
```

## File: test_qualification_suite.py
```python
def test_qualification_suite_contains_baseline_and_faults() -> None
⋮----
cases = _chaos_cases("GC=F", 10)
names = [name for name, _ in cases]
```

## File: test_quality_store.py
```python
def test_quality_store_is_bounded_and_persistent(tmp_path: Path) -> None
⋮----
store = QualityStore(tmp_path / "quality.json")
⋮----
record = store.load()["A:river"]
```

## File: test_quantitative_artifact.py
```python
def _dataset() -> DatasetEvidence
⋮----
def _common(qualification: QuantitativeQualification) -> dict[str, object]
⋮----
def test_quantitative_artifact_hash_matches_content() -> None
⋮----
qualification = QuantitativeQualification(True, 5, 5, ())
artifact = build_quantitative_artifact(
⋮----
def test_artifact_identity_changes_with_config_hash() -> None
⋮----
common = _common(qualification)
⋮----
first = build_quantitative_artifact(config_hash="1" * 64, **common)
second = build_quantitative_artifact(config_hash="2" * 64, **common)
```

## File: test_quantitative_qualification.py
```python
def gate(passed: bool, *reasons: str)
⋮----
def test_quantitative_qualification_requires_all_gates() -> None
⋮----
result = evaluate_quantitative_qualification(
⋮----
def test_quantitative_qualification_aggregates_rejections() -> None
```

## File: test_readiness_evidence.py
```python
def strong_evidence() -> ReadinessEvidence
⋮----
def test_build_readiness_components_from_strong_evidence() -> None
⋮----
components = build_readiness_components(strong_evidence())
⋮----
def test_model_stability_penalizes_small_sample() -> None
⋮----
report = ModelQuality(
⋮----
def test_execution_quality_is_capped_when_allocator_rejects() -> None
⋮----
report = GlobalAllocationReport(
```

## File: test_readiness_handshake.py
```python
def test_readiness_handshake_times_out_without_heartbeat(tmp_path: Path) -> None
⋮----
result = wait_for_worker_readiness(
```

## File: test_readiness_release.py
```python
def composite()
⋮----
def qualification() -> QualificationRecord
⋮----
def trend() -> ReadinessTrend
⋮----
def test_readiness_release_round_trip(tmp_path) -> None
⋮----
comp = composite()
qual = qualification()
gov = GovernorState(verdict="TRADE", reason="healthy", consecutive_halts=0)
res = ResilienceState(mode="NORMAL", instability_status="stable")
chain = ReadinessChainReport(valid=True, records=5, legacy_records=0)
⋮----
release = create_readiness_release(
store = ReadinessReleaseStore(tmp_path / "release.json")
⋮----
loaded = store.load()
⋮----
verification = verify_readiness_release(
⋮----
def test_readiness_release_rejects_changed_governor() -> None
⋮----
gov = GovernorState(verdict="TRADE")
res = ResilienceState(mode="NORMAL")
⋮----
def test_readiness_release_rejects_changed_chain_head() -> None
⋮----
def test_readiness_release_is_content_addressed() -> None
⋮----
first = create_readiness_release(
second = create_readiness_release(
⋮----
def test_readiness_release_rejects_wrong_signing_key() -> None
⋮----
def test_readiness_release_rejects_unsigned_manifest_by_default() -> None
⋮----
def test_readiness_release_store_refuses_overwrite(tmp_path) -> None
```

## File: test_readiness_revocation.py
```python
def test_readiness_revocation_round_trip(tmp_path: Path) -> None
⋮----
store = ReadinessRevocationStore(tmp_path / "revocations.jsonl")
⋮----
record = store.revoke("abc123", reason="superseded")
⋮----
def test_readiness_revocation_is_idempotent(tmp_path: Path) -> None
⋮----
first = store.revoke("abc123", reason="superseded")
second = store.revoke("abc123", reason="duplicate")
```

## File: test_readiness_score.py
```python
def test_composite_readiness_passes_strong_profile() -> None
⋮----
result = evaluate_composite_readiness(
⋮----
def test_composite_readiness_fails_weak_component_even_if_average_is_high() -> None
⋮----
def test_composite_readiness_hash_is_deterministic() -> None
⋮----
components = ReadinessComponents(
first = evaluate_composite_readiness(components)
second = evaluate_composite_readiness(components)
⋮----
def test_custom_weights_are_normalized() -> None
⋮----
def test_readiness_history_round_trip(tmp_path: Path) -> None
⋮----
store = ReadinessHistoryStore(tmp_path / "readiness.jsonl")
⋮----
saved = store.append(result)
loaded = store.list()
⋮----
def test_readiness_history_chain_detects_tampering(tmp_path: Path) -> None
⋮----
first = evaluate_composite_readiness(
second = evaluate_composite_readiness(
⋮----
lines = store.path.read_text(encoding="utf-8").splitlines()
⋮----
report = store.verify_chain()
⋮----
def test_readiness_history_chain_links_records(tmp_path: Path) -> None
⋮----
first = store.append(result)
second = store.append(result)
```

## File: test_readiness_trend.py
```python
def record(score: float, passed: bool = True, offset: int = 0) -> ReadinessHistoryRecord
⋮----
result = evaluate_composite_readiness(
result = type(result)(
⋮----
def test_readiness_trend_is_stable_for_consistent_scores() -> None
⋮----
trend = evaluate_readiness_trend(
⋮----
def test_readiness_trend_detects_declining_score() -> None
⋮----
def test_readiness_trend_requires_full_window() -> None
⋮----
trend = evaluate_readiness_trend([record(95.0), record(95.0)])
```

## File: test_readiness.py
```python
def good_metrics() -> PerformanceMetrics
⋮----
def test_readiness_passes_strong_burn_in() -> None
⋮----
report = evaluate_readiness(
⋮----
def test_readiness_rejects_short_burn_in() -> None
⋮----
def test_readiness_report_exposes_all_structured_checks() -> None
⋮----
by_name = {check.name: check for check in report.checks}
```

## File: test_realized_pnl_accounting.py
```python
def trade(pnl: float, *, pnl_known: bool | None = None) -> TradeSnapshot
⋮----
def test_opening_position_sets_cost_basis_and_realizes_only_costs() -> None
⋮----
fill = calculate_rebalance_fill(
⋮----
def test_adding_to_position_updates_weighted_average_entry() -> None
⋮----
def test_reducing_long_realizes_price_move_less_costs() -> None
⋮----
def test_reducing_short_realizes_short_profit() -> None
⋮----
def test_position_flip_realizes_old_side_and_resets_cost_basis() -> None
⋮----
def test_legacy_position_without_cost_basis_marks_realized_pnl_unknown() -> None
⋮----
def test_performance_excludes_unknown_legacy_pnl_but_counts_trade() -> None
⋮----
metrics = calculate_performance_metrics(
⋮----
def test_trade_snapshot_defaults_legacy_zero_pnl_to_unknown() -> None
⋮----
def test_runtime_state_loads_legacy_json_without_cost_basis(tmp_path) -> None
⋮----
path = tmp_path / "state.json"
⋮----
state = RuntimeStateStore(path).load(RiskConfig().starting_cash)
```

## File: test_recovery_health.py
```python
def test_recovery_health_is_healthy_for_shallow_success(tmp_path: Path) -> None
⋮----
lifecycle = LifecycleEventLog(tmp_path / "lifecycle.jsonl")
⋮----
health = evaluate_recovery_health(lifecycle)
⋮----
health = evaluate_recovery_health(
```

## File: test_recovery.py
```python
def test_recovery_restores_latest_valid_snapshot(tmp_path: Path) -> None
⋮----
artifacts = tmp_path / "artifacts"
⋮----
state = artifacts / "state.json"
⋮----
snapshots = AtomicSnapshotStore(tmp_path / "snapshots")
⋮----
result = recover_latest_consistent_state(
⋮----
audit = AuditLog(artifacts / "audit.jsonl")
⋮----
first = snapshots.create([state])
first_fp = compute_session_fingerprint([state], audit.path)
⋮----
second = snapshots.create([state])
second_fp = compute_session_fingerprint([state], audit.path)
bad_hashes = dict(second_fp.state_hashes)
⋮----
snapshot = snapshots.create([state])
fingerprint = compute_session_fingerprint([state], audit.path)
bad_hashes = dict(fingerprint.state_hashes)
```

## File: test_regime_gate.py
```python
def test_regime_gate_accepts_balanced_regime_results() -> None
⋮----
report = SimpleNamespace(
⋮----
result = evaluate_regime_gate(report)
⋮----
def test_regime_gate_rejects_fragile_regime_profile() -> None
⋮----
result = evaluate_regime_gate(
⋮----
def test_regime_gate_rejects_nan_return_instead_of_passing() -> None
⋮----
def test_regime_gate_rejects_infinite_return_instead_of_passing() -> None
```

## File: test_regime_validation.py
```python
def test_regime_validation_passes_diversified_profile() -> None
⋮----
result = validate_regime_returns(
⋮----
def test_regime_validation_rejects_concentrated_profile() -> None
```

## File: test_regime.py
```python
def test_bull_high_vol_regime() -> None
⋮----
row = pd.Series({"trend_10": 0.03, "trend_30": 0.02, "vol_10": 0.03})
regime = detect_regime(row)
⋮----
def test_sideways_normal_vol_regime() -> None
⋮----
row = pd.Series({"trend_10": 0.001, "trend_30": -0.001, "vol_10": 0.01})
```

## File: test_reliability.py
```python
def write_events(path: Path, events: list[LifecycleEvent]) -> LifecycleEventLog
⋮----
def test_reliability_calculates_state_ratios_and_mttr(tmp_path: Path) -> None
⋮----
start = datetime(2026, 1, 1, tzinfo=UTC)
log = write_events(
⋮----
report = evaluate_reliability(
⋮----
def test_reliability_is_perfect_without_incidents(tmp_path: Path) -> None
```

## File: test_replay.py
```python
def test_replay_comparison_is_deterministic_for_same_audit(tmp_path: Path) -> None
⋮----
path = tmp_path / "audit.jsonl"
⋮----
events = load_audit_events(path, event_filter={"runtime_step"})
report = compare_replays(events, list(events))
```

## File: test_reproducibility.py
```python
def market() -> pd.DataFrame
⋮----
index = pd.date_range("2025-01-01", periods=4, freq="D")
⋮----
def artifact()
⋮----
frame = market()
dataset = build_dataset_evidence(
qualification = QuantitativeQualification(True, 5, 5, ())
⋮----
def test_reproducibility_accepts_exact_inputs() -> None
⋮----
result = verify_quantitative_reproducibility(
⋮----
def test_reproducibility_rejects_dataset_tampering() -> None
⋮----
modified = market()
⋮----
result = verify_quantitative_reproducibility(artifact(), modified)
⋮----
def test_reproducibility_rejects_provider_change() -> None
⋮----
def test_reproducibility_rejects_config_change() -> None
```

## File: test_research_config_validation.py
```python
def test_invalid_research_configuration_fails_closed(factory) -> None
⋮----
def test_valid_research_configurations_remain_supported() -> None
⋮----
walk = WalkForwardConfig(
mtf = MTFBenchmarkConfig(
multi = MultiAssetWalkForwardBacktester(
```

## File: test_resilience_stability.py
```python
def append_transition(log: LifecycleEventLog, from_mode: str, to_mode: str) -> None
⋮----
def test_detects_repeated_mode_oscillation(tmp_path: Path) -> None
⋮----
log = LifecycleEventLog(tmp_path / "lifecycle.jsonl")
sequence = ["NORMAL", "DEGRADED", "NORMAL", "DEGRADED", "NORMAL", "DEGRADED"]
previous = "NORMAL"
⋮----
previous = mode
⋮----
health = evaluate_resilience_stability(
⋮----
def test_detects_excessive_recovery_duration(tmp_path: Path) -> None
⋮----
def test_detects_repeated_cooldowns(tmp_path: Path) -> None
⋮----
def test_marks_extreme_transition_instability_critical(tmp_path: Path) -> None
```

## File: test_resilience.py
```python
def signals(**overrides) -> ResilienceSignals
⋮----
values = {
⋮----
def test_resilience_escalates_to_degraded() -> None
⋮----
decision = evaluate_resilience(
⋮----
def test_resilience_enters_halt_on_critical_recovery_failure() -> None
⋮----
def test_resilience_requires_recovery_confirmations() -> None
⋮----
policy = ResiliencePolicy(recovery_confirmations=2)
first = evaluate_resilience(
second = evaluate_resilience(first.state, signals(), policy)
⋮----
def test_halt_requires_cooldown_before_normal() -> None
⋮----
policy = ResiliencePolicy(cooldown_confirmations=2)
⋮----
def test_resilience_store_persists_state(tmp_path: Path) -> None
⋮----
store = ResilienceStateStore(tmp_path / "resilience.json")
state = ResilienceState(mode="CAUTIOUS", healthy_streak=1, reason="test")
⋮----
def test_adaptive_policy_never_increases_nominal_exposure() -> None
⋮----
base = ResiliencePolicy()
adaptive = adapt_resilience_policy(
⋮----
def test_adaptive_policy_is_unchanged_in_healthy_conditions() -> None
⋮----
def test_adaptive_policy_tightens_degraded_exposure() -> None
⋮----
path = tmp_path / "resilience.json"
⋮----
state = ResilienceStateStore(path).load()
```

## File: test_risk_governor.py
```python
def base_signals(**overrides)
⋮----
values = {
⋮----
def test_governor_trade_when_all_gates_pass() -> None
⋮----
decision = evaluate_governor(base_signals())
⋮----
def test_governor_reduces_on_elevated_risk() -> None
⋮----
decision = evaluate_governor(base_signals(crisis_mode="cautious"))
⋮----
def test_governor_freezes_on_failed_risk_gate() -> None
⋮----
decision = evaluate_governor(base_signals(portfolio_risk_approved=False))
⋮----
def test_governor_flattens_on_extreme_drawdown() -> None
⋮----
decision = evaluate_governor(base_signals(drawdown=0.20))
⋮----
def test_governor_halts_on_critical_data_failure() -> None
⋮----
decision = evaluate_governor(base_signals(data_quality=0.50))
⋮----
def test_failed_stress_test_reduces_instead_of_freezing() -> None
⋮----
decision = evaluate_governor(
⋮----
def test_governor_reduces_when_recovery_health_is_degraded() -> None
⋮----
def test_governor_halts_after_repeated_recovery_failures() -> None
⋮----
def test_governor_halts_on_excessive_recovery_fallback_depth() -> None
⋮----
def test_governor_returns_to_trade_after_recovery_health_normalizes() -> None
⋮----
degraded = evaluate_governor(base_signals(recovery_degraded=True))
healthy = evaluate_governor(base_signals(recovery_degraded=False))
⋮----
decision = evaluate_governor(base_signals(**{field: value}))
```

## File: test_risk_parity.py
```python
def test_risk_parity_weights_are_bounded_and_normalized() -> None
⋮----
rng = np.random.default_rng(5)
base = rng.normal(0, 0.01, 400)
returns = pd.DataFrame(
weights = risk_parity_weights(
```

## File: test_risk.py
```python
def test_low_confidence_is_rejected() -> None
⋮----
engine = RiskEngine(RiskConfig(min_confidence=0.60))
pred = Prediction(side=1, confidence=0.55, probabilities={-1: 0.2, 0: 0.25, 1: 0.55})
snap = PortfolioSnapshot(100_000, 100_000, 100_000)
decision = engine.evaluate(pred, snap)
⋮----
def test_drawdown_limit_is_fail_closed() -> None
⋮----
engine = RiskEngine(RiskConfig(max_drawdown_fraction=0.10))
pred = Prediction(side=1, confidence=0.90, probabilities={-1: 0.05, 0: 0.05, 1: 0.90})
snap = PortfolioSnapshot(89_000, 100_000, 100_000)
⋮----
def test_daily_loss_stop_marks_existing_position_for_exit() -> None
⋮----
engine = RiskEngine(RiskConfig(max_daily_loss_fraction=0.02))
pred = Prediction(
snap = PortfolioSnapshot(
⋮----
def test_low_confidence_rejection_does_not_force_liquidation() -> None
⋮----
engine = RiskEngine(RiskConfig(min_confidence=0.70))
⋮----
def test_invalid_model_confidence_cannot_authorize_exposure(confidence: float) -> None
⋮----
engine = RiskEngine(RiskConfig(min_confidence=0.0))
decision = engine.evaluate(
⋮----
def test_invalid_model_side_is_rejected_before_broker_execution() -> None
⋮----
engine = RiskEngine(RiskConfig())
⋮----
values = {
⋮----
decision = RiskEngine(RiskConfig()).evaluate(
```

## File: test_robustness.py
```python
def test_block_bootstrap_is_deterministic_with_seed() -> None
⋮----
equity = pd.Series(100_000.0 * np.cumprod(1.0 + np.linspace(-0.002, 0.003, 120)))
a = block_bootstrap_returns(equity, simulations=200, block_size=5, random_state=7)
b = block_bootstrap_returns(equity, simulations=200, block_size=5, random_state=7)
```

## File: test_rollback_model.py
```python
def metrics() -> PerformanceMetrics
⋮----
def test_rollback_restores_previous_model_artifact(tmp_path: Path) -> None
⋮----
registry = ChampionRegistry(tmp_path / "champions.jsonl")
store = ModelStore(tmp_path / "models")
⋮----
drift = DriftReport(2.0, 0.0, True, ("feature distribution drift",))
decision = evaluate_health(metrics(), drift)
restored = rollback_if_needed(registry, decision, store)
```

## File: test_runtime_factory.py
```python
def test_isolated_runtime_routes_artifacts_to_workspace(tmp_path: Path) -> None
⋮----
runtime = isolated_multiasset_runtime(tmp_path / "soak")
root = tmp_path / "soak"
```

## File: test_runtime_lock.py
```python
def test_runtime_lock_is_exclusive(tmp_path: Path, monkeypatch) -> None
⋮----
path = tmp_path / "runtime.lock"
⋮----
shared_backend = object()
gold = PaperAutonomousRuntime(
same_gold = PaperAutonomousRuntime(
btc = PaperAutonomousRuntime(
⋮----
custom = tmp_path / "custom.lock"
```

## File: test_runtime_persistence.py
```python
RUNTIME_KEY = "paper:GC=F:5m:online-river:v1"
⋮----
def sample_market(n: int = 100) -> pd.DataFrame
⋮----
idx = pd.date_range("2025-01-01", periods=n, freq="D")
t = np.arange(n, dtype=float)
close = 100.0 + 0.1 * t + 2.0 * np.sin(t / 5.0)
open_ = close * (1.0 + 0.001 * np.sin(t / 3.0))
⋮----
class RecordingPersistence
⋮----
def initialize_schema(self) -> None
⋮----
def load_runtime(self, runtime_key: str, starting_cash: float) -> PersistedRuntime
⋮----
def commit_step(self, runtime_key: str, commit: RuntimeStepCommit) -> CommitOutcome
⋮----
def save_runtime_status(self, runtime_key: str, status: HostedRuntimeStatus) -> None
⋮----
def load_runtime_status(self, runtime_key: str) -> HostedRuntimeStatus | None
⋮----
def _persisted_runtime(*, with_model: bool = True) -> PersistedRuntime
⋮----
state = RuntimeState(
model = serialize_model(RiverDirectionModel()) if with_model else None
⋮----
def test_runtime_commits_one_durable_step() -> None
⋮----
persistence = RecordingPersistence(_persisted_runtime())
runtime = PaperAutonomousRuntime(
⋮----
result = runtime.step(sample_market())
⋮----
def test_runtime_returns_safe_skip_on_revision_conflict() -> None
⋮----
persistence = RecordingPersistence(
⋮----
def test_runtime_rejects_missing_model_for_existing_state() -> None
⋮----
persistence = RecordingPersistence(_persisted_runtime(with_model=False))
⋮----
def intraday_market(n: int = 100) -> pd.DataFrame
⋮----
idx = pd.date_range("2025-01-01 09:00", periods=n, freq="5min")
⋮----
close = 100.0 + 0.02 * t + 0.5 * np.sin(t / 5.0)
⋮----
def test_runtime_preserves_daily_loss_baseline_within_trading_day() -> None
⋮----
market = intraday_market()
probe = PaperAutonomousRuntime(
eligible = probe._eligible_execution_indices(market)
previous = eligible[-2]
target = eligible[-1]
⋮----
persisted = PersistedRuntime(
persistence = RecordingPersistence(persisted)
⋮----
result = runtime.step_at(market, target)
⋮----
def test_runtime_resets_daily_loss_baseline_on_new_trading_day() -> None
⋮----
market = sample_market()
⋮----
previous_day = market.index[-3]
⋮----
expected = 97_900.0
```

## File: test_runtime_state.py
```python
def test_runtime_state_round_trip(tmp_path: Path) -> None
⋮----
store = RuntimeStateStore(tmp_path / "state.json")
state = RuntimeState(
```

## File: test_runtime_status.py
```python
def test_runtime_status_store_round_trip(tmp_path) -> None
⋮----
store = HostedRuntimeStatusStore(tmp_path / "runtime_status.json")
status = HostedRuntimeStatus(
⋮----
# 15m cron permits a longer RUNNING heartbeat, never an indefinitely
# STARTING paper cycle with no completed scheduler delivery.
current = datetime(2026, 9, 15, 16, 5, 1, tzinfo=UTC)
starting = replace(status, engine_status="STARTING", poll_seconds=900.0)
blocked = runtime_status_snapshot(starting, now=current)
⋮----
running = runtime_status_snapshot(
```

## File: test_runtime_targeted_step.py
```python
def sample_market(n: int = 105) -> pd.DataFrame
⋮----
idx = pd.date_range("2025-01-01", periods=n, freq="5min")
t = np.arange(n, dtype=float)
close = 100.0 + 0.1 * t + 2.0 * np.sin(t / 5.0)
open_ = close * (1.0 + 0.001 * np.sin(t / 3.0))
⋮----
def build_file_runtime(tmp_path: Path) -> PaperAutonomousRuntime
⋮----
def test_step_at_processes_requested_execution_bar(tmp_path: Path) -> None
⋮----
df = sample_market()
runtime = build_file_runtime(tmp_path)
target = runtime._eligible_execution_indices(df)[-3]
⋮----
result = runtime.step_at(df, target)
⋮----
def test_step_at_is_idempotent_for_same_execution_bar(tmp_path: Path) -> None
⋮----
target = runtime._eligible_execution_indices(df)[-2]
⋮----
first = runtime.step_at(df, target)
second = runtime.step_at(df, target)
⋮----
def test_step_at_rejects_non_eligible_execution_bar(tmp_path: Path) -> None
⋮----
def test_step_at_cannot_regress_to_older_execution_bar(tmp_path: Path) -> None
⋮----
eligible = runtime._eligible_execution_indices(df)
older = eligible[-4]
newer = eligible[-2]
⋮----
first = runtime.step_at(df, newer)
second = runtime.step_at(df, older)
state = runtime.state_store.load(runtime.risk_config.starting_cash)
⋮----
"""A rejected risk stop must not leave a previously opened position exposed."""
journal = TradeJournal(tmp_path / "trades.jsonl")
runtime = PaperAutonomousRuntime(
decisions = iter((
⋮----
opened = runtime.step_at(df, eligible[-4])
⋮----
stopped = runtime.step_at(df, eligible[-3])
⋮----
still_stopped = runtime.step_at(df, eligible[-2])
⋮----
trades = journal.list()
```

## File: test_runtime.py
```python
def sample_market(n: int = 100) -> pd.DataFrame
⋮----
idx = pd.date_range("2025-01-01", periods=n, freq="D")
t = np.arange(n, dtype=float)
close = 100.0 + 0.1 * t + 2.0 * np.sin(t / 5.0)
open_ = close * (1.0 + 0.001 * np.sin(t / 3.0))
⋮----
def test_runtime_step_is_persistent_and_idempotent(tmp_path: Path) -> None
⋮----
runtime = PaperAutonomousRuntime(
df = sample_market()
⋮----
first = runtime.step(df)
second = runtime.step(df)
⋮----
next_df = sample_market(101)
third = runtime.step(next_df)
```

## File: test_scheduler_endpoint.py
```python
def _free_port() -> int
⋮----
request = Request(url, method=method, headers=headers or {}, data=body)
⋮----
port = _free_port()
thread = Thread(
⋮----
deadline = time.time() + 1.0
⋮----
def test_missing_server_token_fails_closed() -> None
⋮----
calls = 0
⋮----
def run_cycle() -> PaperCycleResult
⋮----
response = handle_scheduler_request(
⋮----
def test_missing_authorization_is_unauthorized() -> None
⋮----
def test_wrong_scheme_is_unauthorized() -> None
⋮----
def test_wrong_bearer_token_is_unauthorized() -> None
⋮----
def test_valid_token_runs_exactly_one_cycle() -> None
⋮----
def test_concurrent_progress_is_successful_noop() -> None
⋮----
def test_storage_failure_is_sanitized() -> None
⋮----
rendered = repr(response.payload)
⋮----
def test_execution_failure_is_sanitized() -> None
⋮----
def test_http_scheduler_rejects_missing_and_wrong_authorization(tmp_path) -> None
⋮----
port = _start_scheduler_dashboard(
url = f"http://127.0.0.1:{port}/internal/paper-cycle"
⋮----
def test_http_scheduler_valid_token_runs_one_cycle_and_ignores_body(tmp_path) -> None
⋮----
def fake_cycle() -> PaperCycleResult
⋮----
def test_http_scheduler_partial_cycle_records_real_http_failure(tmp_path) -> None
⋮----
result = PaperCycleResult(
⋮----
payload = json.loads(body)
⋮----
def test_http_scheduler_other_post_routes_are_not_exposed(tmp_path) -> None
⋮----
def test_http_scheduler_failure_response_never_leaks_secrets(tmp_path) -> None
⋮----
def fail_cycle() -> PaperCycleResult
⋮----
def test_scheduler_telemetry_is_sanitized_and_identifies_cloudflare() -> None
⋮----
response = SchedulerHttpResponse(
⋮----
payload = scheduler_telemetry_payload(response, "cloudflare")
⋮----
def test_scheduler_telemetry_does_not_trust_arbitrary_source_headers() -> None
⋮----
payload = scheduler_telemetry_payload(
⋮----
def test_scheduler_delivery_overview_verifies_three_consecutive_cloudflare_successes() -> None
⋮----
deliveries = tuple(
⋮----
overview = scheduler_delivery_overview(
⋮----
def test_http_scheduler_exposes_durable_cloudflare_delivery_evidence(tmp_path) -> None
⋮----
def test_scheduler_delivery_verification_expires_when_latest_success_is_stale() -> None
⋮----
now = datetime(2026, 9, 21, 17, 0, tzinfo=UTC)
⋮----
overview = scheduler_delivery_overview(deliveries, now=now)
⋮----
def test_scheduler_delivery_overview_rejects_invalid_freshness_window() -> None
⋮----
def test_scheduler_response_exposes_backlog_and_mtf_progress() -> None
⋮----
def test_scheduler_marks_partial_market_cycle_degraded() -> None
⋮----
telemetry = scheduler_telemetry_payload(response, "cloudflare")
⋮----
def test_scheduler_delivery_overview_exposes_recent_failed_delivery() -> None
⋮----
now = datetime(2026, 9, 25, 15, 30, tzinfo=UTC)
deliveries = (
```

## File: test_scheduler_governor.py
```python
class DummyOrchestrator
⋮----
def step(self, df: pd.DataFrame, *, symbol: str)
⋮----
def test_scheduler_stops_after_repeated_governor_halts(tmp_path: Path) -> None
⋮----
store = GovernorStateStore(tmp_path / "governor.json")
⋮----
scheduler = PaperScheduler(
```

## File: test_scheduler_iteration_callback.py
```python
class _GovernorStateStore
⋮----
def load(self)
⋮----
class _Orchestrator
⋮----
def step(self, df: pd.DataFrame, *, symbol: str)
⋮----
class _HealthAwareOrchestrator
⋮----
def __init__(self) -> None
⋮----
def test_scheduler_reports_each_completed_iteration() -> None
⋮----
seen: list[object] = []
scheduler = PaperScheduler(
⋮----
results = scheduler.run()
⋮----
def test_scheduler_can_skip_expensive_health_check() -> None
⋮----
orchestrator = _HealthAwareOrchestrator()
```

## File: test_scheduler.py
```python
class FakeOrchestrator
⋮----
def __init__(self) -> None
⋮----
def step(self, df: pd.DataFrame, *, symbol: str)
⋮----
def test_scheduler_runs_bounded_iterations_without_sleep() -> None
⋮----
orchestrator = FakeOrchestrator()
data = pd.DataFrame({"Close": [1.0, 2.0]})
scheduler = PaperScheduler(
⋮----
results = scheduler.run()
⋮----
def test_scheduler_recovers_from_transient_loader_error() -> None
⋮----
attempts = {"count": 0}
⋮----
def loader() -> pd.DataFrame
⋮----
def test_scheduler_fails_closed_after_repeated_errors() -> None
```

## File: test_sensitivity_gate.py
```python
def test_sensitivity_gate_accepts_stable_neighborhood() -> None
⋮----
results = tuple(result(f"s{i}") for i in range(6))
⋮----
gate = evaluate_sensitivity_gate(results)
⋮----
def test_sensitivity_gate_rejects_narrow_optimum() -> None
⋮----
results = (
⋮----
# These used to pass the gate despite losing money, missing trades,
# or emitting invalid/non-physical research measurements.
losses = tuple(
loss_gate = evaluate_sensitivity_gate(losses)
⋮----
candidates = tuple(invalid for _ in range(6))
decision = evaluate_sensitivity_gate(candidates)
```

## File: test_session_integrity.py
```python
def test_session_fingerprint_changes_with_state(tmp_path: Path) -> None
⋮----
state = tmp_path / "state.json"
audit_path = tmp_path / "audit.jsonl"
⋮----
first = compute_session_fingerprint([state], audit_path)
⋮----
second = compute_session_fingerprint([state], audit_path)
```

## File: test_shadow_challenger.py
```python
def sample_market(n: int = 220) -> pd.DataFrame
⋮----
idx = pd.date_range("2025-01-01", periods=n, freq="5min")
t = np.arange(n, dtype=float)
close = 100.0 + 0.03 * t + 1.5 * np.sin(t / 7.0)
open_ = close * (1.0 + 0.0005 * np.sin(t / 4.0))
⋮----
def test_shadow_challenger_purges_unobservable_training_labels(monkeypatch) -> None
⋮----
market = sample_market()
features = make_features(market)
labels = make_labels(market, horizon_bars=3, return_threshold=0.001)
execution_idx = market.index[-5]
captured: dict[str, object] = {}
⋮----
class RecordingEnsemble
⋮----
def fit(self, x: pd.DataFrame, y: pd.Series) -> None
⋮----
def predict_one(self, row: pd.Series, regime) -> Prediction
⋮----
result = evaluate_shadow_challenger(
⋮----
signal_pos = int(market.index.get_loc(execution_idx)) - 1
train_index = captured["train_index"]
⋮----
expected_label = labels.loc[market.index[signal_pos]]
⋮----
# A forward River-v2 sample uses a *closed* last bar and only matured
# labels; its prediction must not require a future OHLCV row.
live_market = market.tz_localize("UTC")
last_bar_close = live_market.index[-1] + pd.Timedelta(minutes=5)
forward = observe_river_v2_forward(
⋮----
# Research must fail closed when CPU budget expires, without affecting v1.
⋮----
# Reject a future/unfinished candle instead of pretending to have
# published a genuinely live prediction retrospectively.
⋮----
def test_shadow_challenger_skips_when_history_is_insufficient() -> None
⋮----
market = sample_market(90)
⋮----
labels = make_labels(market)
```

## File: test_shadow_promotion_gate.py
```python
river = ModelQuality(
challenger = ModelQuality(
⋮----
def test_shadow_promotion_gate_requires_sufficient_evidence() -> None
⋮----
gate = evaluate_shadow_promotion_gate(comparison(observations=40))
⋮----
def test_shadow_promotion_gate_accepts_stronger_challenger_for_review() -> None
⋮----
gate = evaluate_shadow_promotion_gate(comparison(observations=300))
⋮----
def test_shadow_promotion_gate_rejects_calibration_degradation() -> None
⋮----
gate = evaluate_shadow_promotion_gate(
⋮----
# High aggregate accuracy alone must not qualify an all-flat model.
flat = evaluate_shadow_promotion_gate(
⋮----
# A market with mostly flat realized labels cannot establish
# a meaningful directional trading edge, even at 500 samples.
missing_directional_labels = evaluate_shadow_promotion_gate(
```

## File: test_shadow_quality.py
```python
def test_shadow_quality_compares_both_models_on_identical_labels() -> None
⋮----
comparison = compare_shadow_audit_payloads(
⋮----
# Forward observations are stored one cycle *before* their outcomes.
# Compare them with the same later audit record that holds the v1 side.
audit_rows = []
⋮----
signal = pd.Timestamp("2026-10-21T08:00:00+00:00") + pd.Timedelta(
side = -1 if i % 2 == 0 else 1
⋮----
forward = compare_river_v2_forward_audit_payloads(audit_rows)
⋮----
def test_shadow_quality_ignores_unusable_audit_rows() -> None
⋮----
# Malformed confidence cannot inflate genuine directional evidence.
invalid = compare_shadow_audit_payloads(
⋮----
# No hindsight: malformed, stale or not-yet-matured samples cannot
# manufacture additional v2 forward evidence.
forward = compare_river_v2_forward_audit_payloads(
```

## File: test_smoke_e2e.py
```python
def market(seed: int, n: int = 180) -> pd.DataFrame
⋮----
rng = np.random.default_rng(seed)
index = pd.date_range("2025-01-01", periods=n, freq="D")
returns = rng.normal(0.0003, 0.01, n)
close = 100.0 * np.cumprod(1.0 + returns)
open_ = close * (1.0 + rng.normal(0.0, 0.001, n))
⋮----
def test_end_to_end_paper_smoke(tmp_path: Path) -> None
⋮----
workspace = tmp_path / "workspace"
runtime = isolated_multiasset_runtime(workspace)
markets = {
scheduler = MultiAssetPaperScheduler(
⋮----
results = scheduler.run()
⋮----
result = results[0]
⋮----
heartbeat = (workspace / "heartbeat.json").read_text(encoding="utf-8")
```

## File: test_snapshot_retention.py
```python
def test_snapshot_pruning_keeps_latest_entries(tmp_path: Path) -> None
⋮----
artifacts = tmp_path / "artifacts"
⋮----
state = artifacts / "state.json"
store = AtomicSnapshotStore(tmp_path / "snapshots")
⋮----
removed = store.prune(keep_last=2)
remaining = [
```

## File: test_soak_gate_drawdown.py
```python
def test_soak_gate_rejects_excessive_drawdown() -> None
⋮----
result = SoakResult(
qualification = evaluate_soak_qualification(result)
```

## File: test_soak_gate.py
```python
def test_soak_gate_passes_stable_run() -> None
⋮----
result = SoakResult(
qualification = evaluate_soak_qualification(result)
⋮----
def test_soak_gate_rejects_halted_run() -> None
⋮----
qualification = evaluate_soak_qualification(
⋮----
def test_soak_gate_rejects_invalid_numerical_evidence() -> None
⋮----
valid = SoakResult(
⋮----
report = evaluate_soak_qualification(replace(valid, **{field: invalid}))
⋮----
def test_soak_gate_rejects_inconsistent_cycle_counts() -> None
⋮----
report = evaluate_soak_qualification(result)
⋮----
def test_soak_policy_rejects_nonfinite_thresholds() -> None
```

## File: test_specialist_experts.py
```python
def training_data(n: int = 140) -> tuple[pd.DataFrame, pd.Series]
⋮----
t = np.arange(n, dtype=float)
x = pd.DataFrame(
y = pd.Series(np.where(x["trend_10"] > 0.006, 1, np.where(x["trend_10"] < -0.006, -1, 0)))
⋮----
def test_all_specialist_kinds_train_and_predict() -> None
⋮----
model = SpecialistDirectionModel(kind)
⋮----
pred = model.predict_one(x.loc[120, FEATURES])
```

## File: test_startup_check.py
```python
def test_startup_check_halts_on_invalid_state_file(tmp_path: Path) -> None
⋮----
state = tmp_path / "state.json"
⋮----
governor = GovernorStateStore(tmp_path / "governor.json")
⋮----
report = run_startup_check(
⋮----
def test_startup_check_allows_clean_empty_bootstrap(tmp_path: Path) -> None
⋮----
def test_startup_check_halts_on_invalid_governance_jsonl(tmp_path: Path) -> None
⋮----
lifecycle = tmp_path / "model_lifecycle.jsonl"
⋮----
def test_startup_check_halts_on_corrupted_active_artifact(tmp_path: Path) -> None
⋮----
registry = ChampionRegistry(tmp_path / "champions.jsonl")
lifecycle = LifecycleEventLog(tmp_path / "model_lifecycle.jsonl")
artifact = tmp_path / "model.joblib"
⋮----
def test_startup_check_halts_on_tampered_readiness_history(tmp_path: Path) -> None
⋮----
readiness = ReadinessHistoryStore(tmp_path / "readiness.jsonl")
result = evaluate_composite_readiness(
```

## File: test_state_hash.py
```python
def test_state_hash_is_order_independent() -> None
⋮----
left = {"a": 1, "b": {"x": 2, "y": 3}}
right = {"b": {"y": 3, "x": 2}, "a": 1}
⋮----
def test_file_state_hash_detects_change(tmp_path: Path) -> None
⋮----
path = tmp_path / "state.json"
⋮----
first = file_state_hash(path)
⋮----
second = file_state_hash(path)
```

## File: test_state_snapshot.py
```python
def test_snapshot_create_validate_and_restore(tmp_path: Path) -> None
⋮----
artifacts = tmp_path / "artifacts"
⋮----
state = artifacts / "state.json"
⋮----
store = AtomicSnapshotStore(tmp_path / "snapshots")
snapshot = store.create([state])
⋮----
def test_snapshot_restores_json_and_jsonl_governance_files(tmp_path: Path) -> None
⋮----
quarantine = artifacts / "model_quarantine.json"
champions = artifacts / "champions.jsonl"
lifecycle = artifacts / "model_lifecycle.jsonl"
⋮----
snapshot = store.create([quarantine, champions, lifecycle])
⋮----
def test_snapshot_restores_file_to_original_nested_path(tmp_path: Path) -> None
⋮----
model_dir = artifacts / "models" / "champions"
⋮----
artifact = model_dir / "v2.joblib"
```

## File: test_stress_engine.py
```python
def test_stress_engine_returns_risk_scale() -> None
⋮----
rng = np.random.default_rng(5)
returns = pd.DataFrame(
report = run_stress_test(
⋮----
def test_stress_engine_deleverages_under_tight_loss_limit() -> None
⋮----
rng = np.random.default_rng(8)
```

## File: test_supervisor_clean_exit.py
```python
def test_supervisor_clean_exit_does_not_halt_governor(tmp_path: Path) -> None
⋮----
governor = GovernorStateStore(tmp_path / "governor.json")
supervisor = PaperSupervisor(
⋮----
result = supervisor.run()
```

## File: test_supervisor_crash_loop.py
```python
def test_supervisor_crash_loop_halts_governor(tmp_path: Path) -> None
⋮----
governor = GovernorStateStore(tmp_path / "governor.json")
supervisor = PaperSupervisor(
⋮----
result = supervisor.run()
```

## File: test_supervisor_lease.py
```python
def test_supervisor_lease_is_exclusive_for_current_pid(tmp_path: Path) -> None
⋮----
store = SupervisorLeaseStore(tmp_path / "lease.json")
lease = store.acquire("one")
```

## File: test_supervisor_qualification.py
```python
def test_supervisor_requires_passing_qualification_when_enabled(tmp_path: Path) -> None
⋮----
governor = GovernorStateStore(tmp_path / "governor.json")
supervisor = PaperSupervisor(
⋮----
result = supervisor.run()
```

## File: test_supervisor_state.py
```python
def test_supervisor_state_round_trip(tmp_path: Path) -> None
⋮----
store = SupervisorStateStore(tmp_path / "supervisor.json")
state = store.save(
```

## File: test_supervisor.py
```python
def test_supervisor_stops_for_maintenance_before_worker_start(tmp_path: Path) -> None
⋮----
maintenance = MaintenanceStore(tmp_path / "maintenance.json")
⋮----
supervisor = PaperSupervisor(
⋮----
result = supervisor.run()
⋮----
resilience = ResilienceStateStore(tmp_path / "resilience.json")
⋮----
qualification_store = QualificationStore(tmp_path / "qualification.json")
record = QualificationRecord(
```

## File: test_temporal_cv.py
```python
def market(n: int = 320) -> pd.DataFrame
⋮----
idx = pd.date_range("2023-01-01", periods=n, freq="D")
t = np.arange(n, dtype=float)
close = 100 + 0.04 * t + 4.0 * np.sin(t / 9.0)
open_ = close * (1.0 + 0.001 * np.sin(t / 4.0))
⋮----
def test_temporal_cv_produces_multiple_folds() -> None
⋮----
report = temporal_cross_validate_specialist(
```

## File: test_tuning.py
```python
def metric(total_return: float, sharpe: float, sortino: float, drawdown: float) -> PerformanceMetrics
⋮----
def test_objective_prefers_similar_return_with_lower_drawdown() -> None
⋮----
safer = metric(0.20, 1.1, 1.4, 0.08)
riskier = metric(0.21, 1.1, 1.4, 0.18)
```

## File: test_watchdog_enforcer.py
```python
def test_watchdog_enforcer_halts_on_stale_heartbeat(tmp_path: Path) -> None
⋮----
heartbeat_store = HeartbeatStore(tmp_path / "heartbeat.json")
old = Heartbeat(
⋮----
governor = GovernorStateStore(tmp_path / "governor.json")
⋮----
result = enforce_watchdog(
```

## File: test_watchdog.py
```python
def test_heartbeat_store_and_staleness(tmp_path: Path) -> None
⋮----
store = HeartbeatStore(tmp_path / "heartbeat.json")
hb = store.write("multiasset", 3)
⋮----
old = Heartbeat(
```

## File: test_worker_monitor.py
```python
def test_worker_monitor_stops_process_without_heartbeat(tmp_path: Path) -> None
⋮----
process = subprocess.Popen(
result = monitor_worker(
```

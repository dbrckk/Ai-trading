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
ai_trading/
  __init__.py
  allocation_state.py
  allocator_config_store.py
  allocator_tuning.py
  alpha_allocation.py
  alpha_attribution.py
  asset_classes.py
  audit_chain.py
  audit_integrity.py
  audit.py
  backtest.py
  benchmark_gate.py
  bootstrap_gate.py
  bootstrap_robustness.py
  broker.py
  burnin.py
  calibration_routing.py
  champion_probation.py
  champions.py
  chaos.py
  checkpoint_verification.py
  cli.py
  command_app.py
  compute_budget.py
  confidence_calibration.py
  config.py
  continuous.py
  control_plane.py
  cost_stress_gate.py
  cost_stress.py
  crisis_controller.py
  crisis_gate.py
  crisis_state_store.py
  dashboard.py
  data_quality.py
  data.py
  dataset_evidence.py
  deployment_probe.py
  deployment_readiness.py
  drift_retrain_store.py
  drift.py
  economic_meta_store.py
  economic_meta.py
  engine.py
  ensemble.py
  evolution_manager.py
  evolution.py
  execution_costs.py
  experiments.py
  expert_diversity.py
  expert_factory.py
  expert_lifecycle.py
  expert_pool_manager.py
  expert_pool.py
  expert_returns.py
  expert_sandbox.py
  expert_uncertainty.py
  features.py
  file_persistence.py
  generation_progress.py
  generation_rollback.py
  generations.py
  global_allocator.py
  global_selection.py
  governor_state_store.py
  guardrails.py
  health_server.py
  hosted_runtime.py
  kronos_research.py
  lifecycle_log.py
  maintenance.py
  marginal_alpha.py
  market_freshness.py
  meta_router.py
  meta_store.py
  metrics.py
  model_blend.py
  model_codec.py
  model_quality.py
  model_quarantine.py
  model.py
  mtf_parameter_benchmark.py
  mtf_shadow_challenger.py
  mtf_shadow_config.py
  mtf_shadow_quality.py
  multi_market.py
  multi_timeframe_features.py
  multiasset_backtest.py
  multiasset_checkpoint.py
  multiasset_evolution.py
  multiasset_market_context.py
  multiasset_runtime.py
  multiasset_scheduler.py
  multiasset_state.py
  online.py
  operational_overview.py
  orchestrator.py
  paper_cycle_service.py
  paper_cycle.py
  paper_execution.py
  paper_readiness_evidence.py
  parameter_sensitivity.py
  performance_metrics.py
  performance.py
  persistence_factory.py
  persistence.py
  pnl_attribution.py
  portfolio_intelligence.py
  portfolio_risk.py
  portfolio_selection.py
  portfolio.py
  postgres_persistence.py
  process_watch.py
  promotion_guard.py
  promotion.py
  purged_cv.py
  qualification_guard.py
  qualification_store.py
  qualification_suite.py
  quality_store.py
  quantitative_artifact.py
  quantitative_qualification.py
  readiness_evidence.py
  readiness_handshake.py
  readiness_release.py
  readiness_revocation.py
  readiness_score.py
  readiness_trend.py
  readiness.py
  recovery_health.py
  recovery.py
  regime_gate.py
  regime_validation.py
  regime.py
  reliability.py
  replay.py
  reproducibility.py
  research_model_codec.py
  resilience_stability.py
  resilience.py
  restart_log.py
  risk_governor.py
  risk.py
  river_v2_shadow.py
  robustness.py
  runtime_factory.py
  runtime_lock.py
  runtime_state.py
  runtime_status.py
  runtime.py
  scheduler_endpoint.py
  scheduler_fallback.py
  scheduler.py
  sensitivity_gate.py
  session_integrity.py
  shadow_challenger.py
  shadow_promotion_gate.py
  shadow_quality.py
  soak_gate.py
  soak.py
  specialist_experts.py
  startup_check.py
  state_hash.py
  state_snapshot.py
  stress_engine.py
  supervisor_lease.py
  supervisor_state.py
  supervisor.py
  temporal_cv.py
  trade_journal.py
  tuning.py
  watchdog_enforcer.py
  watchdog.py
  worker_monitor.py
```

# Files

## File: ai_trading/__init__.py
```python
"""Ai-trading package."""
⋮----
__version__ = "0.1.0"
```

## File: ai_trading/allocation_state.py
```python
@dataclass(frozen=True)
class AllocationState
⋮----
weights: dict[str, float]
⋮----
class AllocationStateStore
⋮----
def __init__(self, path: str | Path = "artifacts/global_allocation.json") -> None
⋮----
def load(self) -> pd.Series
⋮----
payload = json.loads(self.path.read_text(encoding="utf-8"))
⋮----
def save(self, weights: pd.Series) -> None
⋮----
temp = self.path.with_suffix(".tmp")
```

## File: ai_trading/allocator_config_store.py
```python
class AllocatorConfigStore
⋮----
def __init__(self, path: str | Path = "artifacts/global_allocator_config.json") -> None
⋮----
def load(self) -> GlobalAllocatorConfig | None
⋮----
payload = json.loads(self.path.read_text(encoding="utf-8"))
⋮----
def save(self, config: GlobalAllocatorConfig) -> None
⋮----
temp = self.path.with_suffix(".tmp")
```

## File: ai_trading/allocator_tuning.py
```python
@dataclass(frozen=True)
class AllocatorTuningResult
⋮----
best_score: float
best_config: GlobalAllocatorConfig
trials: int
⋮----
expected_alpha = train.mean()
quality = (1.0 / train.std(ddof=1).replace(0.0, pd.NA)).fillna(0.0)
⋮----
quality = quality / quality.max()
⋮----
report = allocate_global_capital(
⋮----
returns = test.fillna(0.0).mul(report.weights, axis=1).sum(axis=1)
equity = (1.0 + returns).cumprod() * 100_000.0
metrics = compute_metrics(equity)
⋮----
clean = opportunity_returns.astype(float).dropna()
⋮----
fold_size = len(clean) // (folds + 1)
⋮----
study = optuna.create_study(
⋮----
def objective(trial: optuna.Trial) -> float
⋮----
config = GlobalAllocatorConfig(
⋮----
scores: list[float] = []
⋮----
train_end = fold_size * (fold + 1)
test_end = train_end + fold_size
train = clean.iloc[:train_end]
test = clean.iloc[train_end:test_end]
⋮----
p = study.best_params
best = GlobalAllocatorConfig(
```

## File: ai_trading/alpha_allocation.py
```python
@dataclass(frozen=True)
class AlphaAllocationConfig
⋮----
max_asset_weight: float = 0.35
target_gross_exposure: float = 1.0
min_signal_quality: float = 0.05
⋮----
def __post_init__(self) -> None
⋮----
config = config or AlphaAllocationConfig()
⋮----
alpha = expected_alpha.astype(float)
vol = annualized_volatility.astype(float).replace(0.0, np.nan)
q = quality.reindex(alpha.index).fillna(0.0).astype(float)
⋮----
score = alpha.abs() * q.clip(lower=config.min_signal_quality) / vol
score = score.replace([np.inf, -np.inf], np.nan).fillna(0.0)
⋮----
raw = score / score.sum() * config.target_gross_exposure
raw = raw.clip(upper=config.max_asset_weight)
⋮----
# Iteratively redistribute residual without breaking caps.
result = raw.copy()
⋮----
residual = config.target_gross_exposure - float(result.sum())
⋮----
free = result[result < config.max_asset_weight - 1e-12]
⋮----
increments = free / free.sum() * residual if float(free.sum()) > 0 else residual / len(free)
⋮----
add = float(increments.loc[asset] if hasattr(increments, "loc") else increments)
⋮----
signs = np.sign(alpha)
```

## File: ai_trading/alpha_attribution.py
```python
@dataclass(frozen=True)
class AlphaContribution
⋮----
symbol: str
model: str
regime: str
pnl: float
return_contribution: float
```

## File: ai_trading/asset_classes.py
```python
@dataclass(frozen=True)
class CrisisAssetPolicy
⋮----
disabled_cautious: tuple[str, ...] = ()
disabled_defensive: tuple[str, ...] = ("crypto",)
disabled_preservation: tuple[str, ...] = ("crypto", "energy")
⋮----
def classify_symbol(symbol: str) -> str
⋮----
upper = symbol.upper()
⋮----
policy = policy or CrisisAssetPolicy()
asset_class = classify_symbol(symbol)
⋮----
disabled = policy.disabled_cautious
⋮----
disabled = policy.disabled_defensive
⋮----
disabled = policy.disabled_preservation
⋮----
disabled = ()
```

## File: ai_trading/audit_chain.py
```python
@dataclass(frozen=True)
class AuditChainReport
⋮----
valid: bool
lines: int
invalid_line: int | None
reason: str
legacy_lines: int = 0
⋮----
def _record_hash(record: dict[str, Any]) -> str
⋮----
canonical = json.dumps(record, sort_keys=True, separators=(",", ":"), default=str)
⋮----
def verify_audit_chain(path: str | Path) -> AuditChainReport
⋮----
path = Path(path)
⋮----
expected_prev = "GENESIS"
lines = 0
legacy_lines = 0
chain_started = False
⋮----
record = json.loads(line)
⋮----
has_chain_fields = "hash" in record and "prev_hash" in record
⋮----
expected_prev = "LEGACY"
⋮----
chain_started = True
⋮----
stored_hash = str(record["hash"])
body = {k: v for k, v in record.items() if k != "hash"}
computed = _record_hash(body)
⋮----
expected_prev = stored_hash
⋮----
reason = (
```

## File: ai_trading/audit_integrity.py
```python
@dataclass(frozen=True)
class AuditIntegrityReport
⋮----
valid: bool
lines: int
checksum: str
invalid_line: int | None
⋮----
def verify_jsonl_audit(path: str | Path) -> AuditIntegrityReport
⋮----
path = Path(path)
⋮----
digest = hashlib.sha256()
lines = 0
```

## File: ai_trading/audit.py
```python
def _record_hash(record: dict[str, Any]) -> str
⋮----
canonical = json.dumps(record, sort_keys=True, separators=(",", ":"), default=str)
⋮----
body = {
⋮----
class AuditLog
⋮----
def __init__(self, path: str | Path = "artifacts/audit.jsonl") -> None
⋮----
def _last_hash(self) -> str
⋮----
last_non_empty = ""
⋮----
last_non_empty = line
⋮----
record = json.loads(last_non_empty)
⋮----
def append(self, event: str, payload: dict[str, Any]) -> dict[str, Any]
⋮----
record = build_audit_record(event, payload, self._last_hash())
```

## File: ai_trading/backtest.py
```python
def _compound_step_returns(step_returns: list[float]) -> float
⋮----
growth = 1.0
⋮----
@dataclass(frozen=True)
class WalkForwardConfig
⋮----
min_train_bars: int = 252
test_window_bars: int = 63
max_train_bars: int | None = 1000
periods_per_year: float | None = None
use_ensemble: bool = False
⋮----
def __post_init__(self) -> None
⋮----
def as_dict(self) -> dict[str, int | float | bool | None]
⋮----
@dataclass(frozen=True)
class BacktestReport
⋮----
metrics: PerformanceMetrics
benchmark_metrics: PerformanceMetrics
excess_return: float
trades: int
decisions: int
rejected_decisions: int
folds: int
equity_curve: pd.Series
benchmark_curve: pd.Series
regime_returns: dict[str, float]
⋮----
class WalkForwardBacktester
⋮----
"""Purged walk-forward simulation with next-bar-open execution."""
⋮----
def run(self, df: pd.DataFrame) -> BacktestReport
⋮----
features = make_features(df)
labels = make_labels(
usable = features.dropna().index.intersection(labels.dropna().index)
⋮----
minimum = self.config.min_train_bars + self.config.test_window_bars + 1
⋮----
broker = PaperBroker(self.risk_config)
curve: dict[pd.Timestamp, float] = {}
benchmark_prices: dict[pd.Timestamp, float] = {}
regime_step_returns: dict[str, list[float]] = {}
trades = 0
decisions = 0
rejected = 0
folds = 0
previous_units = broker.state.units
previous_execution_day = None
⋮----
purge = max(1, self.model_config.horizon_bars)
start = self.config.min_train_bars + purge
⋮----
test_end = min(start + self.config.test_window_bars, len(usable) - 1)
train_end = max(0, start - purge)
train_start = 0
⋮----
train_start = max(0, train_end - self.config.max_train_bars)
⋮----
train_idx = usable[train_start:train_end]
test_idx = usable[start:test_end]
⋮----
model = EnsembleDirectionModel(random_state=42 + folds)
⋮----
model = OnlineDirectionModel(random_state=42 + folds)
⋮----
signal_pos = int(df.index.get_loc(signal_idx))
⋮----
execution_idx = df.index[signal_pos + 1]
execution_price = float(df.at[execution_idx, "Open"])
close_price = float(df.at[execution_idx, "Close"])
⋮----
execution_day = pd.Timestamp(execution_idx).date()
⋮----
previous_execution_day = execution_day
equity_before_step = broker.state.equity
feature_row = features.loc[signal_idx, FEATURES]
regime = detect_regime(feature_row)
⋮----
prediction = model.predict_one(feature_row, regime)
⋮----
prediction = model.predict_one(feature_row)
snapshot = PortfolioSnapshot(
decision = self.risk.evaluate(prediction, snapshot)
⋮----
start = test_end
⋮----
equity = pd.Series(curve, dtype=float).sort_index()
benchmark_price_series = pd.Series(benchmark_prices, dtype=float).sort_index()
benchmark = buy_and_hold_equity(
⋮----
periods_per_year = (
metrics = compute_metrics(equity, periods_per_year)
benchmark_metrics = compute_metrics(benchmark, periods_per_year)
⋮----
regime_returns = {
```

## File: ai_trading/benchmark_gate.py
```python
@dataclass(frozen=True)
class BenchmarkGatePolicy
⋮----
min_folds: int = 4
min_trades: int = 20
min_sharpe: float = 0.5
min_sortino: float = 0.7
min_calmar: float = 0.5
max_drawdown: float = 0.25
min_excess_return: float = 0.0
⋮----
@dataclass(frozen=True)
class BenchmarkGateResult
⋮----
passed: bool
reasons: tuple[str, ...]
⋮----
policy = policy or BenchmarkGatePolicy()
reasons: list[str] = []
```

## File: ai_trading/bootstrap_gate.py
```python
@dataclass(frozen=True)
class BootstrapGatePolicy
⋮----
min_probability_positive: float = 0.60
max_probability_loss: float = 0.40
min_lower_return: float = -0.15
max_upper_drawdown: float = 0.30
⋮----
@dataclass(frozen=True)
class BootstrapGateResult
⋮----
passed: bool
reasons: tuple[str, ...]
⋮----
policy = policy or BootstrapGatePolicy()
reasons: list[str] = []
```

## File: ai_trading/bootstrap_robustness.py
```python
@dataclass(frozen=True)
class BootstrapConfig
⋮----
simulations: int = 2000
confidence: float = 0.95
seed: int = 42
block_size: int = 5
⋮----
@dataclass(frozen=True)
class BootstrapReport
⋮----
simulations: int
probability_positive: float
probability_loss: float
median_return: float
lower_return: float
upper_return: float
median_max_drawdown: float
upper_max_drawdown: float
⋮----
config = config or BootstrapConfig()
⋮----
returns = (
⋮----
rng = np.random.default_rng(config.seed)
simulated_returns = np.empty(config.simulations)
simulated_drawdowns = np.empty(config.simulations)
⋮----
sample = _block_bootstrap(
wealth = np.cumprod(1.0 + sample)
⋮----
peak = np.maximum.accumulate(wealth)
drawdown = 1.0 - wealth / peak
⋮----
alpha = (1.0 - config.confidence) / 2.0
⋮----
# A batch of integer draws is RNG-equivalent to one draw per block.
# Vectorized indexing avoids millions of Python list extensions when the
# hosted readiness endpoint bootstraps thousands of historical bars.
count = len(returns)
blocks = (count + block_size - 1) // block_size
starts = rng.integers(0, count - block_size + 1, size=blocks)
indices = (starts[:, None] + np.arange(block_size)).ravel()[:count]
```

## File: ai_trading/broker.py
```python
@dataclass
class BrokerState
⋮----
cash: float
units: float = 0.0
last_price: float = 0.0
peak_equity: float = 0.0
day_start_equity: float = 0.0
average_entry_price: float = 0.0
⋮----
@property
    def equity(self) -> float
⋮----
class PaperBroker
⋮----
def __init__(self, config: RiskConfig) -> None
⋮----
def mark(self, price: float) -> None
⋮----
price = float(price)
⋮----
equity = self.state.equity
⋮----
def reset_day_start(self) -> None
⋮----
def rebalance(self, side: int, target_notional: float, price: float) -> RebalanceFill
⋮----
target_notional = float(target_notional)
⋮----
signed_target_notional = 0.0 if side == 0 else side * target_notional
fill = calculate_rebalance_fill(
```

## File: ai_trading/burnin.py
```python
@dataclass(frozen=True)
class BurnInSnapshot
⋮----
timestamp_utc: str
equity: float
scheduler_errors: int
regimes_covered: int
bootstrap_probability_positive: float
processed_bars: int = 0
⋮----
values = tuple(snapshots)
⋮----
timestamps = pd.to_datetime(
equity = pd.Series(
periods_per_year = infer_periods_per_year(equity.index)
⋮----
class BurnInTracker
⋮----
def __init__(self, path: str | Path = "artifacts/burnin.jsonl") -> None
⋮----
snapshot = BurnInSnapshot(
⋮----
def read(self) -> list[BurnInSnapshot]
⋮----
snapshots: list[BurnInSnapshot] = []
⋮----
payload = json.loads(line)
⋮----
def metrics(self) -> PerformanceMetrics
⋮----
def readiness(self) -> ReadinessReport
⋮----
snapshots = self.read()
⋮----
latest = snapshots[-1]
```

## File: ai_trading/calibration_routing.py
```python
@dataclass(frozen=True)
class CalibrationRoutingPolicy
⋮----
min_multiplier: float = 0.25
ece_penalty_strength: float = 1.5
min_observations: int = 20
⋮----
policy = policy or CalibrationRoutingPolicy()
⋮----
penalty = policy.ece_penalty_strength * max(0.0, float(ece))
```

## File: ai_trading/champion_probation.py
```python
@dataclass(frozen=True)
class ProbationPolicy
⋮----
min_observations: int = 5
max_sharpe_drop: float = 0.30
max_sortino_drop: float = 0.40
max_calmar_drop: float = 0.30
max_drawdown_increase: float = 0.03
hard_max_drawdown_increase: float = 0.07
⋮----
@dataclass(frozen=True)
class ProbationState
⋮----
version: str
baseline_metrics: dict[str, float]
observations: int = 0
status: str = "probation"
failure_count: int = 0
⋮----
@dataclass(frozen=True)
class ProbationResult
⋮----
action: str
reasons: tuple[str, ...]
state: ProbationState
active_champion: ChampionRecord | None
⋮----
class ChampionProbationStore
⋮----
def __init__(self, path: str | Path = "artifacts/champion_probation.json") -> None
⋮----
def load(self) -> ProbationState | None
⋮----
def save(self, state: ProbationState) -> None
⋮----
temp = self.path.with_suffix(".tmp")
⋮----
class ChampionProbationManager
⋮----
def start(self, champion: ChampionRecord) -> ProbationState
⋮----
state = ProbationState(
⋮----
state = self.store.load()
active = self.registry.active()
⋮----
required = ("sharpe", "sortino", "max_drawdown", "calmar")
missing = [
⋮----
reasons = (f"missing probation metrics: {', '.join(sorted(missing))}",)
⋮----
observations = state.observations + 1
baseline = state.baseline_metrics
drawdown_increase = float(metrics["max_drawdown"] - baseline["max_drawdown"])
sharpe_drop = float(baseline["sharpe"] - metrics["sharpe"])
sortino_drop = float(baseline["sortino"] - metrics["sortino"])
calmar_drop = float(baseline["calmar"] - metrics["calmar"])
⋮----
reasons: list[str] = []
⋮----
updated = ProbationState(
⋮----
passed = ProbationState(
⋮----
rolled_back = self.registry.rollback()
failed = ProbationState(
```

## File: ai_trading/champions.py
```python
@dataclass(frozen=True)
class ChampionRecord
⋮----
version: str
model_name: str
score: float
metrics: dict[str, float]
config: dict[str, Any]
promoted_at_utc: str
active: bool = True
⋮----
class ChampionRegistry
⋮----
def __init__(self, path: str | Path = "artifacts/champions.jsonl") -> None
⋮----
def _read(self) -> list[ChampionRecord]
⋮----
records: list[ChampionRecord] = []
⋮----
def list(self) -> list[ChampionRecord]
⋮----
def active(self) -> ChampionRecord | None
⋮----
records = self._read()
updated = [ChampionRecord(**{**asdict(r), "active": False}) for r in records]
promoted = ChampionRecord(
⋮----
current = self.active()
⋮----
promoted = self.promote(
⋮----
decision = evaluate_promotion(
⋮----
def rollback(self) -> ChampionRecord
⋮----
active_idx = next((i for i in range(len(records) - 1, -1, -1) if records[i].active), None)
⋮----
previous = updated[active_idx - 1]
rolled_back = ChampionRecord(**{**asdict(previous), "active": True})
⋮----
def _write(self, records: list[ChampionRecord]) -> None
⋮----
temp = self.path.with_suffix(".tmp")
```

## File: ai_trading/chaos.py
```python
@dataclass(frozen=True)
class ChaosScenario
⋮----
name: str
step: int
symbol: str | None = None
⋮----
copied = {symbol: df.copy() for symbol, df in markets.items()}
⋮----
frame = copied[scenario.symbol]
⋮----
last_close = float(frame["Close"].iloc[-20])
```

## File: ai_trading/checkpoint_verification.py
```python
@dataclass(frozen=True)
class CheckpointVerification
⋮----
valid: bool
matched_checkpoint: bool
reason: str
mismatches: tuple[str, ...]
⋮----
audit_path = Path(audit_path)
snapshot_path = str(snapshot_path)
⋮----
checkpoint = None
⋮----
record = json.loads(line)
⋮----
payload = record.get("payload", {})
⋮----
checkpoint = payload
⋮----
expected = checkpoint.get("state_hashes", {})
mismatches: list[str] = []
⋮----
path = Path(state_file)
name = path.name
actual = file_state_hash(path)
```

## File: ai_trading/cli.py
```python
app = typer.Typer(help="Autonomous trading research CLI")
console = Console()
⋮----
root = Path(workspace)
runtime = isolated_multiasset_runtime(root)
⋮----
def synthetic_market(seed: int, n: int = 180) -> pd.DataFrame
⋮----
rng = np.random.default_rng(seed)
index = pd.date_range("2025-01-01", periods=n, freq="D")
returns = rng.normal(0.0003, 0.01, n)
close = 100.0 * np.cumprod(1.0 + returns)
open_ = close * (1.0 + rng.normal(0.0, 0.001, n))
⋮----
markets = {
scheduler = MultiAssetPaperScheduler(
⋮----
results = scheduler.run()
⋮----
snapshot = scheduler.snapshot_store.latest_valid()
⋮----
table = Table(title="Ai-trading self-test")
⋮----
df = load_history(symbol, period, interval)
engine = TradingEngine()
⋮----
result = TradingEngine().paper_run(df)
⋮----
table = Table(title=f"Paper backtest: {symbol}")
⋮----
risk_config = RiskConfig()
model_config = ModelConfig()
wf_config = WalkForwardConfig(
backtester = WalkForwardBacktester(
report = backtester.run(df)
⋮----
table = Table(title=f"Walk-forward: {symbol}")
⋮----
gate = evaluate_benchmark_gate(report)
⋮----
regime_gate = evaluate_regime_gate(report)
⋮----
bootstrap = bootstrap_equity_curve(report.equity_curve)
bootstrap_gate = evaluate_bootstrap_gate(bootstrap)
⋮----
sensitivity = run_parameter_sensitivity(backtester, df)
sensitivity_gate = evaluate_sensitivity_gate(sensitivity)
⋮----
cost_stress = run_cost_stress(backtester, df)
cost_stress_gate = evaluate_cost_stress_gate(cost_stress)
⋮----
quantitative = evaluate_quantitative_qualification(
⋮----
dataset = build_dataset_evidence(
config_payload = {
config_hash = sha256(
artifact = build_quantitative_artifact(
⋮----
baseline_cfg = WalkForwardConfig(
ensemble_cfg = WalkForwardConfig(
⋮----
baseline = WalkForwardBacktester(
ensemble = WalkForwardBacktester(
⋮----
decision = evaluate_challenger(baseline.metrics, ensemble.metrics)
⋮----
table = Table(title=f"Champion vs challenger: {symbol}")
⋮----
report = WalkForwardBacktester(
bootstrap = block_bootstrap_returns(
⋮----
table = Table(title=f"Robustness bootstrap: {symbol}")
⋮----
result = tune_walk_forward(df, trials=trials, use_ensemble=True)
⋮----
table = Table(title=f"Optuna tuning: {symbol}")
⋮----
features = make_features(df).dropna()
split = max(60, int(len(features) * 0.75))
reference_features = features.iloc[:split]
recent_features = features.iloc[split:]
⋮----
strategy_returns = report.equity_curve.pct_change().dropna()
return_split = max(20, int(len(strategy_returns) * 0.75))
drift = detect_drift(
regime_check = validate_regime_returns(report.regime_returns)
health = evaluate_health(report.metrics, drift)
⋮----
table = Table(title=f"Health check: {symbol}")
⋮----
registry = ChampionRegistry()
active = registry.active()
⋮----
restored = registry.rollback()
⋮----
champion_metrics = baseline.metrics
⋮----
champion_metrics = PerformanceMetrics(**active.metrics)
⋮----
result = run_learning_cycle(
⋮----
table = Table(title=f"Learning cycle: {symbol}")
⋮----
result = PaperAutonomousRuntime(
⋮----
table = Table(title=f"Autonomous paper runtime: {symbol}")
⋮----
orchestrator = AutonomousPaperOrchestrator(
scheduler = PaperScheduler(
⋮----
last = results[-1]
⋮----
table = Table(title=f"Autonomous paper loop: {symbol}")
⋮----
names = [s.strip() for s in symbols.split(",") if s.strip()]
⋮----
closes = {}
⋮----
df = load_history(name, period, interval)
⋮----
close_frame = pd.DataFrame(closes).dropna()
returns = close_frame.pct_change().dropna()
weights = inverse_volatility_weights(
notionals = target_notionals(equity, weights)
risk = evaluate_portfolio_risk(
⋮----
table = Table(title="Multi-asset portfolio analysis")
⋮----
bootstrap = block_bootstrap_returns(report.equity_curve)
readiness = evaluate_readiness(
⋮----
table = Table(title=f"Paper readiness: {symbol}")
⋮----
markets = {name: load_history(name, period, interval) for name in names}
result = MultiAssetPaperRuntime().step(markets)
⋮----
table = Table(title="Multi-asset paper runtime")
⋮----
weights_table = Table(title="Target allocation")
⋮----
report = MultiAssetWalkForwardBacktester().run(markets)
⋮----
table = Table(title="Multi-asset walk-forward")
⋮----
result = validate_specialist(df, kind=kind)
⋮----
pool = ExpertPoolStore()
name = f"{symbol}:{kind}"
⋮----
reconciled = reconcile_pool(pool.load())
⋮----
record = reconciled[name]
⋮----
table = Table(title=f"Expert sandbox: {name}")
⋮----
result = refresh_expert_pool(df, symbol=symbol)
⋮----
table = Table(title=f"Expert pool refresh: {symbol}")
⋮----
result = run_expert_factory(
⋮----
table = Table(title=f"Expert factory: {symbol}")
⋮----
result = run_evolution_cycle(
⋮----
table = Table(title=f"Expert evolution: {symbol}")
⋮----
@app.command("generation-rollback")
def generation_rollback() -> None
⋮----
generations = GenerationStore()
result = rollback_generation(pool, generations)
⋮----
table = Table(title="Generation rollback")
⋮----
result = run_multiasset_evolution_cycle(
⋮----
table = Table(title="Multi-asset expert evolution")
⋮----
series = {}
alpha = {}
quality = {}
⋮----
ret = df["Close"].astype(float).pct_change().dropna()
key = f"{name}|baseline|all"
⋮----
frame = pd.DataFrame(series).dropna()
report = allocate_global_capital(
⋮----
table = Table(title="Global capital allocator")
⋮----
result = tune_global_allocator(
⋮----
table = Table(title="Global allocator tuning")
⋮----
@app.command("crisis-status")
def crisis_status() -> None
⋮----
state = CrisisStateStore().load()
limits = limits_for_state(state)
⋮----
table = Table(title="Crisis controller status")
⋮----
@app.command("risk-governor-status")
def risk_governor_status() -> None
⋮----
state = GovernorStateStore().load()
⋮----
table = Table(title="Risk governor status")
⋮----
@app.command("system-status")
def system_status() -> None
⋮----
status = read_control_plane()
⋮----
table = Table(title="AI Trading control plane")
⋮----
names = tuple(s.strip() for s in symbols.split(",") if s.strip())
⋮----
qualification = QualificationStore(qualification_path).load()
⋮----
resilience = ResilienceStateStore(resilience_path).load()
governor = GovernorStateStore(governor_path).load()
lifecycle = LifecycleEventLog(lifecycle_path)
reliability = evaluate_reliability(lifecycle, resilience)
readiness_store = ReadinessHistoryStore(readiness_history_path)
history = readiness_store.list()
chain = readiness_store.verify_chain()
⋮----
composite = history[-1].result
trend = evaluate_readiness_trend(history)
⋮----
readiness = evaluate_deployment_readiness(
blocking = tuple(
⋮----
quantitative_artifact = load_quantitative_artifact(
⋮----
benchmark_data = load_history(
reproducibility = verify_quantitative_reproducibility(
⋮----
signing_key = os.getenv(signing_key_env)
⋮----
release = create_readiness_release(
⋮----
release = ReadinessReleaseStore(release_path).load()
⋮----
record = ReadinessRevocationStore(revocations_path).revoke(
⋮----
resilience_store = ResilienceStateStore(resilience_path)
resilience = resilience_store.load()
⋮----
readiness_history = readiness_store.list()
readiness_chain = readiness_store.verify_chain()
composite = readiness_history[-1].result if readiness_history else None
trend = evaluate_readiness_trend(readiness_history)
release_store = ReadinessReleaseStore(release_path)
release = release_store.load()
revocation_store = ReadinessRevocationStore(revocations_path)
release_verification = None
⋮----
quantitative_evidence_hash = (
quantitative_reproducible = False
quantitative_evidence_age_hours = None
dataset_observation_age_hours = None
⋮----
created_at = datetime.fromisoformat(quantitative_artifact.created_at_utc)
⋮----
created_at = created_at.replace(tzinfo=UTC)
quantitative_evidence_age_hours = max(
last_observation = datetime.fromisoformat(
⋮----
last_observation = last_observation.replace(tzinfo=UTC)
dataset_observation_age_hours = max(
⋮----
quantitative_reproducible = verify_quantitative_reproducibility(
⋮----
quantitative_evidence_hash = ""
⋮----
release_verification = verify_readiness_release(
⋮----
table = Table(title="Paper-to-live deployment readiness")
⋮----
def loader() -> dict[str, pd.DataFrame]
⋮----
table = Table(title="Multi-asset paper loop")
⋮----
@app.command("watchdog-status")
def watchdog_status() -> None
⋮----
heartbeat_store = HeartbeatStore("artifacts/multiasset_heartbeat.json")
heartbeat = heartbeat_store.load()
audit_path = "artifacts/multiasset_audit.jsonl"
audit = verify_jsonl_audit(audit_path)
chain = verify_audit_chain(audit_path)
snapshot = AtomicSnapshotStore().latest_valid()
⋮----
table = Table(title="Paper watchdog status")
⋮----
result = enforce_watchdog(
⋮----
table = Table(title="Watchdog enforcement")
⋮----
store = MaintenanceStore()
⋮----
@app.command("supervisor-status")
def supervisor_status() -> None
⋮----
lease = SupervisorLeaseStore().load()
maintenance_state = MaintenanceStore().load()
⋮----
table = Table(title="Paper supervisor status")
⋮----
@app.command("metrics")
def metrics() -> None
⋮----
server = HealthServer(host=host, port=port)
⋮----
command = [
⋮----
runtime = MultiAssetPaperRuntime()
supervisor = PaperSupervisor(
result = supervisor.run()
⋮----
table = Table(title="Paper supervisor result")
⋮----
chaos = ()
⋮----
target = chaos_symbol.strip() or names[0]
chaos = (
⋮----
result = run_multiasset_soak(
⋮----
table = Table(title="Multi-asset paper soak")
⋮----
qualification = evaluate_soak_qualification(result)
⋮----
result = run_qualification_suite(
⋮----
table = Table(title="Paper qualification suite")
```

## File: ai_trading/command_app.py
```python
PAPER_CYCLE_POLL_SECONDS = 300.0
⋮----
settings = ProductionPaperCycleSettings(
⋮----
result = run_production_paper_cycle(settings)
```

## File: ai_trading/compute_budget.py
```python
@dataclass(frozen=True)
class ComputeBudget
⋮----
total_units: float = 100.0
exploration_fraction: float = 0.10
⋮----
budget = budget or ComputeBudget()
active = {
⋮----
exploration = budget.total_units * budget.exploration_fraction
exploitation = budget.total_units - exploration
⋮----
raw = {
total = sum(raw.values())
⋮----
base_explore = exploration / len(active)
```

## File: ai_trading/confidence_calibration.py
```python
@dataclass(frozen=True)
class CalibrationReport
⋮----
raw_confidence: float
calibrated_confidence: float
expected_calibration_error: float
observations: int
⋮----
def _bin_index(confidence: float, bins: int) -> int
⋮----
confidences = np.asarray(record.confidences, dtype=float)
predictions = np.asarray(record.predictions, dtype=int)
labels = np.asarray(record.labels, dtype=int)
correct = (predictions == labels).astype(float)
⋮----
bin_ids = np.asarray([_bin_index(value, bins) for value in confidences])
target_bin = _bin_index(raw_confidence, bins)
mask = bin_ids == target_bin
⋮----
calibrated = float(raw_confidence)
⋮----
empirical_correct = float(correct[mask].sum())
count = int(mask.sum())
calibrated = (
⋮----
ece = 0.0
total = len(confidences)
⋮----
current = bin_ids == bin_id
count = int(current.sum())
⋮----
mean_confidence = float(confidences[current].mean())
accuracy = float(correct[current].mean())
⋮----
report = calibration_report(
⋮----
raw = max(1e-12, float(prediction.confidence))
shrink = min(1.0, report.calibrated_confidence / raw)
uniform = 1.0 / 3.0
⋮----
probabilities = {
⋮----
total = sum(probabilities.values())
⋮----
side = max(probabilities, key=probabilities.get)
⋮----
calibrated_prediction = Prediction(
```

## File: ai_trading/config.py
```python
@dataclass(frozen=True)
class RiskConfig
⋮----
starting_cash: float = 100_000.0
max_position_fraction: float = 0.10
max_daily_loss_fraction: float = 0.02
max_drawdown_fraction: float = 0.10
min_confidence: float = 0.56
transaction_cost_bps: float = 2.0
slippage_bps: float = 1.0
⋮----
def __post_init__(self) -> None
⋮----
value = float(getattr(self, name))
⋮----
@dataclass(frozen=True)
class ModelConfig
⋮----
horizon_bars: int = 1
return_threshold: float = 0.001
```

## File: ai_trading/continuous.py
```python
@dataclass(frozen=True)
class ContinuousCycleResult
⋮----
tuning: TuningResult
promotion: PromotionDecision
regime_validation: RegimeValidation
robustness: BootstrapReport
promoted: bool
champion_version: str | None
⋮----
tuning = tune_walk_forward(df, trials=trials, use_ensemble=True)
⋮----
risk = RiskConfig(
model_config = ModelConfig(
wf = WalkForwardConfig(
⋮----
challenger = WalkForwardBacktester(
⋮----
promotion = evaluate_challenger(champion_metrics, challenger.metrics)
regime_validation = validate_regime_returns(challenger.regime_returns)
robustness = block_bootstrap_returns(challenger.equity_curve)
⋮----
promoted = (
⋮----
version = None
⋮----
version = f"{symbol}-ensemble-{len(registry.list()) + 1}"
⋮----
features = make_features(df)
labels = make_labels(
final_model = EnsembleDirectionModel(random_state=42)
⋮----
store = model_store or ModelStore()
```

## File: ai_trading/control_plane.py
```python
@dataclass(frozen=True)
class ControlPlaneStatus
⋮----
governor_verdict: str
governor_reason: str
crisis_mode: str
recovery_streak: int
promotions_allowed: bool
scheduler_should_run: bool
⋮----
governor_store = governor_store or GovernorStateStore()
crisis_store = crisis_store or CrisisStateStore()
lifecycle_log = lifecycle_log or LifecycleEventLog()
resilience_store = resilience_store or ResilienceStateStore()
governor = governor_store.load()
crisis = crisis_store.load()
⋮----
recovery_health = evaluate_recovery_health(lifecycle_log)
resilience = resilience_store.load()
promotions = (
scheduler_should_run = (
```

## File: ai_trading/cost_stress_gate.py
```python
@dataclass(frozen=True)
class CostStressGatePolicy
⋮----
min_pass_ratio: float = 0.67
min_excess_return: float = -0.05
min_sharpe: float = 0.0
max_drawdown: float = 0.30
⋮----
@dataclass(frozen=True)
class CostStressGateResult
⋮----
passed: bool
scenarios: int
passing_scenarios: int
pass_ratio: float
worst_excess_return: float
worst_sharpe: float
worst_drawdown: float
reasons: tuple[str, ...]
⋮----
policy = policy or CostStressGatePolicy()
⋮----
passing = [
ratio = len(passing) / len(results)
reasons: list[str] = []
```

## File: ai_trading/cost_stress.py
```python
@dataclass(frozen=True)
class CostStressScenario
⋮----
name: str
transaction_cost_bps: float
slippage_bps: float
⋮----
@dataclass(frozen=True)
class CostStressResult
⋮----
scenario: CostStressScenario
total_return: float
excess_return: float
sharpe: float
max_drawdown: float
trades: int
⋮----
DEFAULT_COST_STRESS_SCENARIOS = (
⋮----
results: list[CostStressResult] = []
⋮----
risk = replace(
stressed = WalkForwardBacktester(
⋮----
def _result(scenario: CostStressScenario, report: BacktestReport) -> CostStressResult
```

## File: ai_trading/crisis_controller.py
```python
@dataclass(frozen=True)
class CrisisPolicy
⋮----
cautious_stress_scale: float = 0.85
defensive_stress_scale: float = 0.60
preservation_stress_scale: float = 0.30
cautious_drawdown: float = 0.04
defensive_drawdown: float = 0.08
preservation_drawdown: float = 0.12
recover_drawdown: float = 0.03
recovery_confirmations: int = 3
⋮----
@dataclass(frozen=True)
class CrisisState
⋮----
mode: str = "normal"
recovery_streak: int = 0
⋮----
@dataclass(frozen=True)
class CrisisDecision
⋮----
state: CrisisState
exposure_scale: float
max_active_experts: int
asset_limit_fraction: float
allow_new_promotions: bool
reason: str
⋮----
_MODE_ORDER = {
⋮----
policy = policy or CrisisPolicy()
desired = _desired_mode(
⋮----
current_rank = _MODE_ORDER[current.mode]
desired_rank = _MODE_ORDER[desired]
⋮----
state = CrisisState(mode=desired, recovery_streak=0)
reason = "risk conditions deteriorated"
⋮----
healthy = (
streak = current.recovery_streak + 1 if healthy else 0
⋮----
next_rank = max(0, current_rank - 1)
next_mode = next(k for k, v in _MODE_ORDER.items() if v == next_rank)
state = CrisisState(mode=next_mode, recovery_streak=0)
reason = "recovery confirmed with hysteresis"
⋮----
state = CrisisState(mode=current.mode, recovery_streak=streak)
reason = "holding crisis mode until recovery confirmation"
⋮----
state = CrisisState(mode=current.mode, recovery_streak=0)
reason = "mode unchanged"
⋮----
def limits_for_state(state: CrisisState) -> CrisisDecision
```

## File: ai_trading/crisis_gate.py
```python
crisis_store = crisis_store or CrisisStateStore()
governor_store = governor_store or GovernorStateStore()
```

## File: ai_trading/crisis_state_store.py
```python
class CrisisStateStore
⋮----
def __init__(self, path: str | Path = "artifacts/crisis_state.json") -> None
⋮----
def load(self) -> CrisisState
⋮----
payload = json.loads(self.path.read_text(encoding="utf-8"))
⋮----
def save(self, state: CrisisState) -> None
⋮----
temp = self.path.with_suffix(".tmp")
```

## File: ai_trading/dashboard.py
```python
_STORAGE_ERROR_STATUS: dict[str, object] = {
⋮----
snapshot = runtime_status_snapshot(status, now=now)
⋮----
def _display_money(value: float | None) -> str
⋮----
def _display_units(value: float | None) -> str
⋮----
def _display_ratio(value: float | None) -> str
⋮----
delivery_count = int(overview["delivery_count"])
verified = bool(overview["cloudflare_delivery_verified"])
fresh = bool(overview["cloudflare_delivery_fresh"])
age = overview["last_delivery_age_seconds"]
freshness = float(overview["freshness_seconds"])
last_ok = overview.get("last_ok")
recent = age is not None and float(age) <= freshness
⋮----
state = "VERIFIED"
state_class = "status-ok"
⋮----
state = "WAITING"
state_class = "status-warn"
⋮----
state = "DEGRADED"
state_class = "status-error"
⋮----
state = "STALE"
⋮----
state = "COLLECTING"
⋮----
age_display = "-" if age is None else f"{float(age):.0f}s"
freshness_display = f"{freshness:.0f}s"
⋮----
def _trade_pnl_known(trade: object) -> bool
⋮----
marker = getattr(trade, "pnl_known", None)
⋮----
def _display_trade_pnl(trade: object) -> str
⋮----
def _equity_chart_svg(snapshots: tuple[BurnInSnapshot, ...]) -> str
⋮----
values = [float(snapshot.equity) for snapshot in snapshots]
width = 900.0
height = 240.0
padding = 18.0
low = min(values)
high = max(values)
span = high - low
⋮----
span = max(abs(high), 1.0) * 0.01
⋮----
usable_width = width - 2 * padding
usable_height = height - 2 * padding
points: list[str] = []
⋮----
x = padding + usable_width * index / (len(values) - 1)
y = padding + usable_height * (high - value) / (high - low)
⋮----
change = values[-1] - values[0]
direction_class = "positive" if change >= 0 else "negative"
⋮----
def _readiness_number(check: ReadinessCheck, value: float) -> str
⋮----
def _readiness_panel(report: ReadinessReport | None) -> str
⋮----
rows = []
⋮----
state = "pass" if check.passed else "fail"
label = "PASS" if check.passed else "FAIL"
value = _readiness_number(check, check.value)
threshold = _readiness_number(check, check.threshold)
⋮----
storage_error = False
runtime_revision: int | None = None
runtime_model = None
persisted_runtime = None
durable_runtime = persistence is not None and runtime_key is not None
⋮----
multi_market_view = bool(markets and len(markets) > 1)
recent = persistence.list_trades(
persisted = persistence.load_runtime(runtime_key, starting_cash)
persisted_runtime = persisted
state = persisted.state
runtime_revision = persisted.revision
runtime_model = persisted.model
runtime_status = persistence.load_runtime_status(runtime_key)
load_performance = getattr(persistence, "load_trade_performance", None)
load_portfolio_performance = getattr(
⋮----
multi_runtime_keys = tuple(
trade_performance = load_portfolio_performance(
performance_scope = "full persisted cross-market history (allocation-adjusted)"
performance_is_recent = False
⋮----
trade_performance = calculate_allocated_performance_metrics(
performance_scope = "latest 200 cross-market trade events (allocation-adjusted)"
performance_is_recent = True
⋮----
trade_performance = load_performance(runtime_key)
performance_scope = "full persisted history"
⋮----
trade_performance = calculate_performance_metrics(recent)
performance_scope = "latest 200 trade events"
⋮----
load_burnin = getattr(persistence, "list_burnin_snapshots", None)
burnin_snapshots = tuple(load_burnin(runtime_key)) if callable(load_burnin) else ()
load_regimes = getattr(persistence, "list_regimes", None)
regimes = tuple(load_regimes(runtime_key)) if callable(load_regimes) else ()
burnin_metrics = (
⋮----
recent = ()
state = None
runtime_status = None
trade_performance = None
burnin_snapshots = ()
regimes = ()
burnin_metrics = None
performance_scope = "unavailable"
storage_error = True
⋮----
recent = journal.list(limit=200)
state = state_store.load(starting_cash) if state_store is not None else None
runtime_status = (
⋮----
trades = reversed(recent)
⋮----
realized_pnl: float | None = None
trade_count: int | None = None
pnl_observations: int | None = None
pnl_coverage_total: int | None = None
pnl_coverage_recent = False
wins: int | None = None
losses: int | None = None
win_rate: float | None = None
active_symbols: int | None = None
cash: float | None = None
units: float | None = None
equity: float | None = None
position_value: float | None = None
⋮----
realized_pnl = trade_performance.realized_pnl
trade_count = trade_performance.trade_count
persisted_observations = getattr(
⋮----
pnl_observations = sum(1 for trade in recent if _trade_pnl_known(trade))
⋮----
pnl_observations = int(persisted_observations)
pnl_coverage_total = len(recent) if performance_is_recent else trade_count
pnl_coverage_recent = performance_is_recent
⋮----
realized_pnl = None
wins = sum(
losses = sum(
win_rate = (wins / (wins + losses)) if wins + losses else 0.0
active_symbols = len({trade.symbol for trade in recent})
cash = state.cash if state is not None else starting_cash
units = state.units if state is not None else 0.0
last_price = state.last_price if state is not None else 0.0
equity = state.cash + state.units * state.last_price if state is not None else starting_cash
position_value = units * last_price
⋮----
last_processed = (
processed_bars_display = (
⋮----
runtime_snapshot = _public_runtime_snapshot(runtime_status, now=now)
engine_status = "ERROR" if storage_error else str(runtime_snapshot["engine_status"])
market = (
last_cycle = (
last_heartbeat = (
heartbeat_age_value = None if storage_error else runtime_snapshot["heartbeat_age_seconds"]
heartbeat_age = (
runtime_revision_display = (
cycle_errors_display = (
⋮----
model_display = "-"
model_checksum = "-"
⋮----
model_display = f"{runtime_model.format} v{runtime_model.version}"
model_checksum = runtime_model.sha256[:12]
⋮----
operational_alerts: list[str] = []
⋮----
operational_alerts_display = (
⋮----
signal = "-"
confidence = "-"
risk_decision = "-"
decision_reason = "storage unavailable" if storage_error else "-"
⋮----
paper_signal = paper_signal_snapshot(
⋮----
decision_reason = (
⋮----
decision_reason = "worker heartbeat expired"
⋮----
signal = str(paper_signal["signal"])
confidence = f"{float(paper_signal['confidence']):.1%}"
risk_decision = "APPROVED" if runtime_status.approved else "REJECTED"
decision_reason = runtime_status.decision_reason or decision_reason
⋮----
risk_decision = str(paper_signal["signal_state"])
⋮----
risk_decision = "SKIPPED"
⋮----
rows = '<tr><td colspan="9">Storage unavailable.</td></tr>'
⋮----
rows = "".join(
⋮----
rows = '<tr><td colspan="9">No trades recorded yet.</td></tr>'
⋮----
trade_count_display = "-" if trade_count is None else str(trade_count)
pnl_display = _display_money(realized_pnl)
⋮----
pnl_coverage_display = "-"
⋮----
recent_suffix = " recent" if pnl_coverage_recent else ""
pnl_coverage_display = (
win_rate_display = "-" if win_rate is None else f"{win_rate:.1%}"
wins_losses_display = "-" if wins is None or losses is None else f"{wins} / {losses}"
active_symbols_display = "-" if active_symbols is None else str(active_symbols)
average_pnl_display = _display_money(
profit_factor_display = _display_ratio(
max_drawdown_display = _display_money(
burnin_bars = (
burnin_bars_display = "-" if burnin_bars is None else str(burnin_bars)
burnin_target = ReadinessPolicy().min_burn_in_bars
burnin_progress = (
burnin_progress_display = f"{burnin_progress:.0%}"
burnin_return_display = (
burnin_drawdown_display = (
equity_chart = _equity_chart_svg(burnin_snapshots)
bootstrap_probability = bootstrap_positive_probability(
bootstrap_probability_display = (
readiness_policy = ReadinessPolicy()
bootstrap_threshold = readiness_policy.min_positive_bootstrap_probability
scheduler_reliable = (
scheduler_reliability_display = (
regimes_covered = len(regimes)
regimes_covered_display = "-" if storage_error else str(regimes_covered)
regimes_threshold = readiness_policy.min_regimes_covered
regime_names_display = "none" if not regimes else " · ".join(regimes)
readiness_report = None
⋮----
readiness_report = evaluate_readiness(
readiness_display = (
readiness_checks_display = (
sharpe_display = "-" if burnin_metrics is None else f"{burnin_metrics.sharpe:.2f}"
sortino_display = "-" if burnin_metrics is None else f"{burnin_metrics.sortino:.2f}"
readiness_panel = _readiness_panel(readiness_report)
status_class = (
⋮----
scheduler_panel = ""
⋮----
list_deliveries = getattr(persistence, "list_scheduler_deliveries", None)
deliveries = tuple(list_deliveries(limit=20)) if callable(list_deliveries) else ()
scheduler_overview = scheduler_delivery_overview(deliveries)
scheduler_delivery_count = int(scheduler_overview["delivery_count"])
scheduler_successes = int(
scheduler_last_source = str(scheduler_overview["last_source"] or "-")
scheduler_last_status = (
scheduler_last_delivery = str(
⋮----
scheduler_panel = f"""
⋮----
scheduler_panel = """
⋮----
market_panel = ""
⋮----
snapshot = build_multi_market_overview(
portfolio = snapshot["portfolio"]
cards = []
⋮----
overview = item["overview"]
shadow = overview.get("shadow_challenger", {})
gate = shadow.get("promotion_gate", {})
mtf_shadow = overview.get("mtf_shadow_challenger", {})
mtf_gate = mtf_shadow.get("promotion_gate", {})
status = str(overview.get("engine_status", "UNKNOWN"))
status_css = (
sleeve_equity = item.get("equity")
sleeve_pnl = item.get("pnl")
processed = overview.get("processed_bars")
cycle_duration = item.get("cycle_duration_seconds")
cycle_duration_display = (
heartbeat_age_seconds = item.get("heartbeat_age_seconds")
heartbeat_age_display = (
freshness = str(item.get("freshness") or "OFF")
session_open = item.get("session_open")
session_display = (
mtf_candidate = mtf_shadow.get("candidate_config")
mtf_horizon = mtf_shadow.get("horizon_minutes")
mtf_candidate_name = (
mtf_label = (
mtf_cycle_display = (
observations = shadow.get("observations", 0)
mtf_observations = mtf_shadow.get("observations", 0)
mtf_directional = mtf_shadow.get("directional_observations", 0)
mtf_directional_rate = float(mtf_shadow.get("directional_rate", 0.0) or 0.0)
mtf_distribution = mtf_shadow.get("label_distribution", {})
review = "ELIGIBLE" if gate.get("eligible_for_review") else "COLLECTING"
mtf_review = (
mtf_score_delta = mtf_shadow.get("score_delta")
mtf_score_display = (
signal = item.get("signal") or "-"
signal_state = str(item.get("signal_state") or "UNAVAILABLE")
signal_time = html.escape(str(item.get("signal_time") or "-"))
paper_risk_reason = html.escape(str(item.get("decision_reason") or "-"))
signal_age = item.get("signal_age_seconds")
signal_age_display = (
signal_css = {
market_confidence = item.get("confidence")
confidence_value = (
confidence_display = (
shadow_progress = min(100.0, float(observations) / 250.0 * 100.0)
mtf_shadow_progress = min(
mtf_directional_progress = min(
market_tone = {
market_mark = {
pnl_css = (
reason = html.escape(str(item.get("reason") or "waiting for next eligible bar"))
⋮----
raw_portfolio_pnl = portfolio["pnl"]
portfolio_pnl = (
portfolio_pnl_css = (
market_panel = (
⋮----
effective_settings = settings or HostedPaperSettings.from_env()
# Render publishes the exact deployed Git commit at runtime.
revision = os.getenv("RENDER_GIT_COMMIT", "").strip().lower()
deployed_commit = revision if fullmatch(r"[0-9a-f]{40}", revision) else None
effective_markets = configured_markets_from_env()
journal = TradeJournal(journal_path)
state_store = RuntimeStateStore(state_path)
runtime_status_store = HostedRuntimeStatusStore(status_path)
⋮----
backend = persistence
⋮----
backend = build_paper_persistence(pool_connections=True)
⋮----
root = Path(state_path).parent
backend = FilePaperPersistence(
⋮----
runtime_key = effective_settings.runtime_key
effective_scheduler_token = (
# A hosted external scheduler needs an authenticated entry point and a
# shared durable database. In local/offline mode these are optional.
external_scheduler_configured = (
effective_cycle_executor = paper_cycle_executor
⋮----
cycle_settings = ProductionPaperCycleSettings(
⋮----
# Cloudflare runs every 15 minutes; heartbeat cadence is not the 5m bar size.
# Keep the 5m cadence for manually initiated/in-process cycles.
⋮----
def execute_paper_cycle() -> PaperCycleResult
⋮----
effective_cycle_executor = execute_paper_cycle
⋮----
def load_status_snapshot() -> dict[str, object]
⋮----
class Handler(BaseHTTPRequestHandler)
⋮----
server_version = "AITrading"
sys_version = ""
⋮----
def end_headers(self) -> None
⋮----
def _write_response_body(self, body: bytes) -> None
⋮----
body = json.dumps(payload, sort_keys=True).encode()
⋮----
def do_GET(self) -> None
⋮----
path = urlsplit(self.path).path.rstrip("/")
⋮----
deliveries = backend.list_scheduler_deliveries(limit=20)
⋮----
liveness: dict[str, object] = {"web_healthy": True}
⋮----
snapshot = load_status_snapshot()
storage_healthy = snapshot.get("storage_healthy") is not False
ready = storage_healthy and external_scheduler_configured
⋮----
payload = render_dashboard(
⋮----
def do_POST(self) -> None
⋮----
response = handle_scheduler_request(
telemetry = scheduler_telemetry_payload(
⋮----
def log_message(self, format: str, *args: object) -> None
```

## File: ai_trading/data_quality.py
```python
@dataclass(frozen=True)
class DataQualityReport
⋮----
score: float
completeness: float
duplicate_fraction: float
invalid_price_fraction: float
ohlc_violation_fraction: float
stale_fraction: float
valid: bool
reasons: tuple[str, ...]
gap_fraction: float = 0.0
⋮----
required_columns = ["Open", "High", "Low", "Close"]
missing_columns = [column for column in required_columns if column not in df.columns]
⋮----
sample = df.loc[:, required_columns].tail(lookback).copy()
⋮----
completeness = float(sample.notna().mean().mean())
duplicate_fraction = float(df.index.duplicated(keep=False).mean())
⋮----
invalid_prices = (sample <= 0).any(axis=1)
invalid_price_fraction = float(invalid_prices.mean())
⋮----
high = sample["High"]
low = sample["Low"]
open_ = sample["Open"]
close = sample["Close"]
violations = (
ohlc_violation_fraction = float(violations.fillna(True).mean())
⋮----
close_changes = close.pct_change().abs()
stale_fraction = float((close_changes.fillna(0.0) == 0.0).mean())
⋮----
gap_fraction = 1.0
⋮----
deltas = sample.index.to_series().diff().dropna()
positive = deltas[deltas > pd.Timedelta(0)]
⋮----
cadence = positive.median()
⋮----
gap_fraction = float((positive > cadence * 1.5).mean())
⋮----
score = (
⋮----
reasons: list[str] = []
```

## File: ai_trading/data.py
```python
class MarketDataProvider(Protocol)
⋮----
"""Minimal provider contract used by the trading runtime."""
⋮----
name: str
⋮----
def download(self, symbol: str, *, period: str, interval: str) -> pd.DataFrame: ...
⋮----
@dataclass(frozen=True)
class YahooFinanceProvider
⋮----
name: str = "yahoo"
⋮----
def download(self, symbol: str, *, period: str, interval: str) -> pd.DataFrame
⋮----
DEFAULT_MARKET_DATA_PROVIDERS: tuple[MarketDataProvider, ...] = (YahooFinanceProvider(),)
⋮----
_OHLC_COLUMNS = ("Open", "High", "Low", "Close")
_HISTORY_COLUMNS = (*_OHLC_COLUMNS, "Volume")
⋮----
def _normalize_history_frame(df: pd.DataFrame) -> pd.DataFrame
⋮----
frame = df.copy()
⋮----
missing = set(_HISTORY_COLUMNS).difference(frame.columns)
⋮----
result = frame.loc[:, list(_HISTORY_COLUMNS)].copy()
⋮----
result = result.dropna(subset=list(_OHLC_COLUMNS))
⋮----
result = result.sort_index()
⋮----
result = result.loc[~result.index.duplicated(keep="last")].copy()
⋮----
prices = result.loc[:, list(_OHLC_COLUMNS)]
⋮----
violations = (
⋮----
provider_chain = DEFAULT_MARKET_DATA_PROVIDERS if providers is None else providers
⋮----
last_error: Exception | None = None
attempts = 0
⋮----
frame = provider.download(symbol, period=period, interval=interval)
⋮----
except Exception as exc:  # noqa: BLE001 - providers raise backend-specific errors
last_error = exc
```

## File: ai_trading/dataset_evidence.py
```python
@dataclass(frozen=True)
class DatasetEvidence
⋮----
schema_version: int
provider: str
acquired_at_utc: str
rows: int
first_timestamp: str
last_timestamp: str
columns: tuple[str, ...]
data_hash: str
⋮----
normalized = df.copy()
⋮----
normalized = normalized.sort_index()
columns = tuple(str(column) for column in normalized.columns)
records = [
payload = {
canonical = json.dumps(
⋮----
def dataset_evidence_hash(evidence: DatasetEvidence) -> str
```

## File: ai_trading/deployment_probe.py
```python
"""Read-only probe of the deployed dashboard; no broker or scheduler requests."""
⋮----
@dataclass(frozen=True)
class ProbeCheck
⋮----
endpoint: str
ok: bool
detail: str
⋮----
def _fetch_json(base_url: str, endpoint: str, timeout: float) -> tuple[dict, str]
⋮----
request = Request(
⋮----
status = response.status
body = response.read(128_001)
⋮----
# Only surface known, public readiness error codes. Never print
# arbitrary upstream bodies, database URLs or exception details.
⋮----
explanation = json.loads(exc.read(4096))
reason = explanation.get("error") if isinstance(explanation, dict) else None
⋮----
payload = json.loads(body)
⋮----
"""Check web process, durable readiness and three market cards independently."""
⋮----
checks: list[ProbeCheck] = []
⋮----
valid = payload.get("web_healthy") is True
detail = "web_healthy" if valid else "liveness_unhealthy"
⋮----
valid = payload.get("deployed_commit") == expected_sha
detail = (
⋮----
valid = (
detail = "storage_ready" if valid else "storage_or_configuration_unready"
⋮----
markets = payload.get("markets")
symbols = (
expected = {"GC=F", "^GDAXI", "BTC-USD"}
portfolio = payload.get("portfolio")
complete = (
valid = expected.issubset(symbols) and complete
⋮----
detail = "missing_market_cards"
⋮----
detail = "portfolio_or_market_unavailable"
⋮----
detail = "three_markets_healthy"
⋮----
def main() -> int
⋮----
parser = argparse.ArgumentParser(description="Probe read-only Trading AI endpoints")
⋮----
args = parser.parse_args()
checks = probe_dashboard(args.base_url, timeout=args.timeout, expected_sha=args.expected_sha)
```

## File: ai_trading/deployment_readiness.py
```python
@dataclass(frozen=True)
class DeploymentReadinessPolicy
⋮----
min_reliability_score: float = 95.0
min_normal_ratio: float = 0.95
max_halt_ratio: float = 0.005
max_mttr_seconds: float = 300.0
min_observation_seconds: float = 604_800.0
max_qualification_age_hours: float = 24.0
require_composite_score: bool = True
min_composite_score: float = 90.0
require_stable_trend: bool = True
require_release_manifest: bool = True
require_quantitative_reproducibility: bool = True
max_quantitative_evidence_age_hours: float = 24.0
max_dataset_observation_age_hours: float = 72.0
⋮----
@dataclass(frozen=True)
class DeploymentReadiness
⋮----
allowed: bool
reasons: tuple[str, ...]
⋮----
policy = policy or DeploymentReadinessPolicy()
reasons: list[str] = []
⋮----
guard = validate_qualification_record(
```

## File: ai_trading/drift_retrain_store.py
```python
@dataclass(frozen=True)
class DriftRetrainRecord
⋮----
processed_bar: int
max_psi: float
correlation_shift: float
⋮----
class DriftRetrainStore
⋮----
def load(self) -> dict[str, DriftRetrainRecord]
⋮----
payload = json.loads(self.path.read_text(encoding="utf-8"))
⋮----
record = self.load().get(symbol)
⋮----
records = self.load()
⋮----
temp = self.path.with_suffix(".tmp")
```

## File: ai_trading/drift.py
```python
@dataclass(frozen=True)
class DriftReport
⋮----
feature_drift_score: float
return_drift_score: float
drifted: bool
reasons: tuple[str, ...]
⋮----
def _standardized_mean_shift(reference: pd.Series, recent: pd.Series) -> float
⋮----
ref = reference.astype(float).dropna()
cur = recent.astype(float).dropna()
⋮----
scale = float(ref.std(ddof=1))
⋮----
scale = 1e-12
⋮----
feature_scores = [
feature_score = max(feature_scores, default=0.0)
return_score = _standardized_mean_shift(reference_returns, recent_returns)
⋮----
reasons: list[str] = []
⋮----
@dataclass(frozen=True)
class DistributionDriftReport
⋮----
max_psi: float
mean_psi: float
correlation_shift: float
risk_multiplier: float
retrain_requested: bool
drifted_features: tuple[str, ...]
⋮----
ref = reference.astype(float).replace([np.inf, -np.inf], np.nan).dropna()
cur = recent.astype(float).replace([np.inf, -np.inf], np.nan).dropna()
⋮----
quantiles = np.unique(
⋮----
ref_bins = pd.cut(ref, bins=quantiles, include_lowest=True)
cur_bins = pd.cut(cur, bins=quantiles, include_lowest=True)
⋮----
ref_freq = ref_bins.value_counts(sort=False, normalize=True)
cur_freq = cur_bins.value_counts(sort=False, normalize=True).reindex(
⋮----
epsilon = 1e-6
ref_values = np.clip(ref_freq.to_numpy(dtype=float), epsilon, None)
cur_values = np.clip(cur_freq.to_numpy(dtype=float), epsilon, None)
⋮----
common = [
⋮----
psi_by_feature = {
max_psi = max(psi_by_feature.values(), default=0.0)
mean_psi = (
⋮----
ref_corr = reference_features[common].astype(float).corr().fillna(0.0)
cur_corr = recent_features[common].astype(float).corr().fillna(0.0)
correlation_shift = float(
⋮----
drifted = tuple(
severity = max(
risk_multiplier = float(np.clip(1.0 - 0.5 * severity, 0.25, 1.0))
retrain_requested = bool(
```

## File: ai_trading/economic_meta_store.py
```python
class EconomicMetaStore
⋮----
def __init__(self, path: str | Path = "artifacts/economic_meta.json") -> None
⋮----
def load(self) -> dict[str, EconomicMetaStats]
⋮----
payload = json.loads(self.path.read_text(encoding="utf-8"))
⋮----
def save(self, data: dict[str, EconomicMetaStats]) -> None
⋮----
temp = self.path.with_suffix(".tmp")
⋮----
data = self.load()
current = data.get(key, EconomicMetaStats())
updated = update_economic_meta(
```

## File: ai_trading/economic_meta.py
```python
@dataclass(frozen=True)
class EconomicMetaConfig
⋮----
pnl_weight: float = 1.0
turnover_penalty: float = 0.20
cost_penalty: float = 1.0
drawdown_penalty: float = 0.75
decay: float = 0.97
exploration_floor: float = 0.05
⋮----
@dataclass(frozen=True)
class EconomicMetaStats
⋮----
score: float = 0.0
decayed_pnl: float = 0.0
decayed_turnover: float = 0.0
decayed_costs: float = 0.0
decayed_drawdown: float = 0.0
observations: int = 0
⋮----
config = config or EconomicMetaConfig()
⋮----
d = float(np.clip(config.decay, 0.0, 1.0))
decayed_pnl = d * stats.decayed_pnl + float(pnl) / equity
decayed_turnover = d * stats.decayed_turnover + abs(float(turnover)) / equity
decayed_costs = d * stats.decayed_costs + abs(float(costs)) / equity
decayed_drawdown = d * stats.decayed_drawdown + max(0.0, float(drawdown))
⋮----
score = (
⋮----
# Smooth positive mapping with an exploration floor.
mapped = 1.0 / (1.0 + np.exp(-stats.score * 10.0))
```

## File: ai_trading/engine.py
```python
@dataclass(frozen=True)
class RunResult
⋮----
starting_equity: float
final_equity: float
total_return: float
max_drawdown: float
trades: int
decisions: int
⋮----
class TradingEngine
⋮----
def train(self, df: pd.DataFrame) -> None
⋮----
x = make_features(df)
y = make_labels(
⋮----
def paper_run(self, df: pd.DataFrame, train_fraction: float = 0.60) -> RunResult
⋮----
usable = x.dropna().index.intersection(y.dropna().index)
⋮----
split = max(50, int(len(usable) * train_fraction))
train_idx = usable[:split]
test_idx = usable[split:]
⋮----
broker = PaperBroker(self.risk_config)
start = broker.state.equity
max_dd = 0.0
trades = 0
decisions = 0
previous_units = broker.state.units
previous_execution_day = None
⋮----
price = float(df.at[idx, "Close"])
⋮----
execution_day = pd.Timestamp(idx).date()
⋮----
previous_execution_day = execution_day
⋮----
prediction = self.model.predict_one(x.loc[idx, FEATURES])
snapshot = PortfolioSnapshot(
decision = self.risk.evaluate(prediction, snapshot)
⋮----
dd = 1.0 - broker.state.equity / broker.state.peak_equity
max_dd = max(max_dd, dd)
⋮----
final = broker.state.equity
```

## File: ai_trading/ensemble.py
```python
@dataclass
class _Member
⋮----
name: str
model: object
weight: float
⋮----
class EnsembleDirectionModel
⋮----
classes = np.array([-1, 0, 1], dtype=int)
⋮----
def fit(self, x: pd.DataFrame, y: pd.Series) -> None
⋮----
x2 = x.loc[:, self.feature_names].dropna()
y2 = y.reindex(x2.index).dropna().astype(int)
x2 = x2.loc[y2.index]
⋮----
def _regime_weights(self, regime: MarketRegime) -> dict[str, float]
⋮----
weights = {member.name: member.weight for member in self.members}
⋮----
total = sum(weights.values())
⋮----
def predict_one(self, row: pd.Series, regime: MarketRegime) -> Prediction
⋮----
x = pd.DataFrame([row.loc[list(self.feature_names)].astype(float).to_dict()])
weights = self._regime_weights(regime)
aggregate = {-1: 0.0, 0: 0.0, 1: 0.0}
⋮----
proba = member.model.predict_proba(x)[0]
model_classes = member.model.classes_
⋮----
side = max(aggregate, key=aggregate.get)
```

## File: ai_trading/evolution_manager.py
```python
@dataclass(frozen=True)
class EvolutionCycleResult
⋮----
evaluated: int
accepted: int
replaced: int
generation: int
rolled_back: bool
mutated: tuple[ExpertCandidate, ...]
⋮----
def _record_to_candidate(record: ExpertRecord) -> ExpertCandidate | None
⋮----
match = re.search(r":h(?P<horizon>\d+):t(?P<threshold>[^:]+)", record.name)
⋮----
horizon = int(match.group("horizon"))
threshold = float(match.group("threshold"))
⋮----
series: dict[str, pd.Series] = {}
⋮----
candidate = _record_to_candidate(record)
⋮----
def _portfolio_score(returns: pd.Series | None) -> float
⋮----
equity = (1.0 + returns).cumprod() * 100_000.0
⋮----
store = store or ExpertPoolStore()
generation_store = generation_store or GenerationStore()
records = store.load()
⋮----
parents = top_parents(records, symbol=symbol, limit=parent_limit)
baseline_returns = _active_pool_returns(df, records, symbol)
⋮----
mutations: list[ExpertCandidate] = []
parent_by_child: dict[str, str] = {}
⋮----
parent = _record_to_candidate(parent_record)
⋮----
children = mutate_expert(
⋮----
accepted = 0
replaced = 0
next_generation = generation_store.current_generation() + 1
⋮----
report: TemporalCVReport = temporal_cross_validate_specialist(
candidate_returns = specialist_return_series(
⋮----
portfolio_approved = baseline_returns is None
⋮----
marginal = evaluate_marginal_alpha(
⋮----
active_scores = [
incumbent_score = min(active_scores) if active_scores else 0.0
replacement = evaluate_portfolio_replacement(
portfolio_approved = replacement.replace
⋮----
existing = records.get(candidate.name)
⋮----
reconciled = reconcile_pool(records)
⋮----
new_returns = _active_pool_returns(df, reconciled, symbol)
active_names = [
snapshot = generation_store.snapshot(
⋮----
rolled_back = False
snapshots = generation_store.snapshots()
⋮----
progress = compare_generations(snapshots[-2], snapshots[-1])
⋮----
rolled_back = True
```

## File: ai_trading/evolution.py
```python
@dataclass(frozen=True)
class MutationConfig
⋮----
horizon_steps: tuple[int, ...] = (-2, -1, 1, 2)
threshold_multipliers: tuple[float, ...] = (0.5, 0.75, 1.25, 1.5)
max_mutations_per_parent: int = 4
⋮----
config = config or MutationConfig()
mutations: list[ExpertCandidate] = []
⋮----
horizon = max(1, parent.horizon_bars + step)
⋮----
threshold = max(1e-5, parent.return_threshold * mult)
⋮----
dedup: dict[str, ExpertCandidate] = {m.name: m for m in mutations}
⋮----
eligible = [
```

## File: ai_trading/execution_costs.py
```python
_ENV_NAME = "AI_TRADING_EXECUTION_COSTS_JSON"
⋮----
config = base or RiskConfig()
payload_text = os.getenv(_ENV_NAME, "") if raw is None else raw
payload_text = payload_text.strip()
⋮----
payload = json.loads(payload_text)
⋮----
override = payload.get(symbol)
⋮----
allowed = {"transaction_cost_bps", "slippage_bps"}
unknown = set(override).difference(allowed)
⋮----
values: dict[str, float] = {}
⋮----
value = float(override[name])
```

## File: ai_trading/experiments.py
```python
class ExperimentRegistry
⋮----
"""Append-only JSONL registry for reproducible research runs."""
⋮----
def __init__(self, path: str | Path = "artifacts/experiments.jsonl") -> None
⋮----
metric_payload = asdict(metrics) if is_dataclass(metrics) else dict(metrics)
record = {
```

## File: ai_trading/expert_diversity.py
```python
@dataclass(frozen=True)
class DiversityReport
⋮----
max_pair_correlation: float
mean_pair_correlation: float
diversified: bool
⋮----
clean = expert_returns.astype(float).dropna()
⋮----
corr = clean.corr().abs()
pairs: list[float] = []
⋮----
value = corr.at[left, right]
⋮----
maximum = max(pairs)
mean = sum(pairs) / len(pairs)
```

## File: ai_trading/expert_factory.py
```python
@dataclass(frozen=True)
class ExpertCandidate
⋮----
name: str
kind: str
horizon_bars: int
return_threshold: float
compute_cost: float
⋮----
@dataclass(frozen=True)
class FactoryConfig
⋮----
horizons: tuple[int, ...] = (1, 3, 5)
return_thresholds: tuple[float, ...] = (0.0005, 0.001, 0.002)
kinds: tuple[str, ...] = ("trend", "range", "high_vol")
max_candidates: int = 12
max_promotions_per_run: int = 3
⋮----
@dataclass(frozen=True)
class FactoryResult
⋮----
evaluated: int
promoted: int
candidates: tuple[ExpertCandidate, ...]
⋮----
config = config or FactoryConfig()
candidates: list[ExpertCandidate] = []
⋮----
cost_by_kind = {
⋮----
name = f"{symbol}:{kind}:h{horizon}:t{threshold:g}"
⋮----
store = store or ExpertPoolStore()
⋮----
records = store.load()
⋮----
evaluated: list[ExpertCandidate] = []
before_active = {
⋮----
result = validate_specialist(
⋮----
existing = records.get(candidate.name)
economic_score = existing.economic_score if existing else 0.0
combined = (
⋮----
reconciled = reconcile_pool(records)
⋮----
newly_active = [
⋮----
reconciled = {
newly_active = []
⋮----
keep = set(
⋮----
promoted = sum(
```

## File: ai_trading/expert_lifecycle.py
```python
@dataclass(frozen=True)
class ExpertLifecyclePolicy
⋮----
min_observations: int = 20
retire_below_score: float = -0.02
retrain_below_score: float = -0.005
⋮----
@dataclass(frozen=True)
class ExpertLifecycleDecision
⋮----
action: str
reason: str
⋮----
policy = policy or ExpertLifecyclePolicy()
```

## File: ai_trading/expert_pool_manager.py
```python
@dataclass(frozen=True)
class PoolRefreshResult
⋮----
records: dict[str, ExpertRecord]
sandbox: dict[str, SandboxResult]
⋮----
store = store or ExpertPoolStore()
policy = policy or ExpertPoolPolicy()
⋮----
sandbox_results: dict[str, SandboxResult] = {}
records = store.load()
⋮----
compute_costs = {
⋮----
result = validate_specialist(df, kind=kind)
⋮----
name = f"{symbol}:{kind}"
⋮----
previous = records.get(name)
economic_score = previous.economic_score if previous is not None else 0.0
observations = (
combined = (
⋮----
reconciled = reconcile_pool(records, policy)
⋮----
reconciled = {
```

## File: ai_trading/expert_pool.py
```python
@dataclass(frozen=True)
class ExpertRecord
⋮----
name: str
kind: str
status: str
score: float = 0.0
economic_score: float = 0.0
validation_score: float = 0.0
observations: int = 0
compute_cost: float = 1.0
⋮----
@dataclass(frozen=True)
class ExpertPoolPolicy
⋮----
max_active_experts: int = 5
max_total_experts: int = 12
min_promotion_score: float = 0.55
prune_below_score: float = 0.20
⋮----
class ExpertPoolStore
⋮----
def __init__(self, path: str | Path = "artifacts/expert_pool.json") -> None
⋮----
def load(self) -> dict[str, ExpertRecord]
⋮----
payload = json.loads(self.path.read_text(encoding="utf-8"))
⋮----
def save(self, records: dict[str, ExpertRecord]) -> None
⋮----
temp = self.path.with_suffix(".tmp")
⋮----
def upsert(self, record: ExpertRecord) -> None
⋮----
records = self.load()
⋮----
active = {
⋮----
raw = {}
⋮----
quality = max(exploration_floor, record.score)
efficiency = quality / max(0.1, record.compute_cost)
⋮----
total = sum(raw.values())
⋮----
policy = policy or ExpertPoolPolicy()
ordered = sorted(
⋮----
result: dict[str, ExpertRecord] = {}
active_count = 0
⋮----
status = record.status
⋮----
status = "pruned"
⋮----
status = "active"
⋮----
status = "challenger"
```

## File: ai_trading/expert_returns.py
```python
features = make_features(df)
labels = make_labels(
usable = features.dropna().index.intersection(labels.dropna().index)
⋮----
split = max(80, int(len(usable) * train_fraction))
train_idx = usable[:split]
test_idx = usable[split:]
⋮----
model = SpecialistDirectionModel(kind)
⋮----
values: dict[pd.Timestamp, float] = {}
⋮----
pos = int(df.index.get_loc(idx))
⋮----
next_idx = df.index[pos + 1]
prediction = model.predict_one(features.loc[idx])
market_return = float(df.at[next_idx, "Close"] / df.at[next_idx, "Open"] - 1.0)
⋮----
def equal_weight_pool_returns(series: dict[str, pd.Series]) -> pd.Series
⋮----
frame = pd.DataFrame(series).dropna()
```

## File: ai_trading/expert_sandbox.py
```python
@dataclass(frozen=True)
class SandboxResult
⋮----
metrics: PerformanceMetrics
accuracy: float
validation_score: float
observations: int
⋮----
features = make_features(df)
labels = make_labels(
usable = features.dropna().index.intersection(labels.dropna().index)
⋮----
split = max(80, int(len(usable) * train_fraction))
train_idx = usable[:split]
test_idx = usable[split:]
⋮----
model = SpecialistDirectionModel(kind)
⋮----
equity = [100_000.0]
correct = 0
active = 0
⋮----
pred = model.predict_one(features.loc[idx])
label = int(labels.loc[idx])
⋮----
current_pos = int(df.index.get_loc(idx))
next_idx = df.index[current_pos + 1]
ret = float(df.at[next_idx, "Close"] / df.at[next_idx, "Open"] - 1.0)
⋮----
curve = pd.Series(equity, dtype=float)
metrics = compute_metrics(curve)
observations = max(1, len(test_idx) - 1)
accuracy = correct / observations
validation_score = max(
```

## File: ai_trading/expert_uncertainty.py
```python
@dataclass(frozen=True)
class ExpertUncertainty
⋮----
disagreement: float
consensus_confidence: float
risk_multiplier: float
experts: int
⋮----
names = list(predictions)
⋮----
normalized = {name: 1.0 / len(names) for name in names}
⋮----
raw = {name: max(0.0, float(weights.get(name, 0.0))) for name in names}
total = sum(raw.values())
normalized = (
⋮----
classes = (-1, 0, 1)
consensus = np.zeros(3, dtype=float)
vectors: dict[str, np.ndarray] = {}
⋮----
vector = np.asarray(
total = float(vector.sum())
⋮----
vector = np.full(3, 1.0 / 3.0)
⋮----
vector = vector / total
⋮----
disagreement = 0.0
⋮----
# Total variation distance is bounded to [0, 1].
tv = 0.5 * float(np.abs(vector - consensus).sum())
⋮----
risk_multiplier = max(
consensus_confidence = float(consensus.max())
```

## File: ai_trading/features.py
```python
FEATURES = [
⋮----
CHALLENGER_FEATURES = [
⋮----
def make_features(df: pd.DataFrame) -> pd.DataFrame
⋮----
close = df["Close"].astype(float)
high = df["High"].astype(float)
low = df["Low"].astype(float)
volume = df["Volume"].astype(float)
⋮----
out = pd.DataFrame(index=df.index)
⋮----
vol_mean = volume.rolling(20).mean()
raw_vol_std = volume.rolling(20).std()
vol_std = raw_vol_std.replace(0, np.nan)
volume_z20 = (volume - vol_mean) / vol_std
⋮----
def make_challenger_features(df: pd.DataFrame) -> pd.DataFrame
⋮----
"""Build richer research features without changing the production feature set."""
⋮----
out = make_features(df).copy()
open_ = df["Open"].astype(float)
⋮----
returns = close.pct_change()
⋮----
previous_close = close.shift(1)
true_range = pd.concat(
⋮----
delta = close.diff()
average_gain = delta.clip(lower=0.0).rolling(14).mean()
average_loss = (-delta.clip(upper=0.0)).rolling(14).mean()
relative_strength = average_gain / average_loss.replace(0.0, np.nan)
rsi = 100.0 - (100.0 / (1.0 + relative_strength))
rsi = rsi.mask((average_loss == 0.0) & (average_gain > 0.0), 100.0)
rsi = rsi.mask((average_loss == 0.0) & (average_gain == 0.0), 50.0)
⋮----
rolling_low = low.rolling(20).min()
rolling_high = high.rolling(20).max()
range_width = (rolling_high - rolling_low).replace(0.0, np.nan)
⋮----
raw_volume_20 = volume.rolling(20).mean()
volume_20 = raw_volume_20.replace(0.0, np.nan)
volume_ratio = volume.rolling(5).mean() / volume_20 - 1.0
⋮----
future_return = df["Close"].shift(-horizon_bars) / df["Close"] - 1.0
labels = pd.Series(0, index=df.index, dtype="int8")
```

## File: ai_trading/file_persistence.py
```python
class FilePaperPersistence(PaperPersistence)
⋮----
"""Compatibility backend over the existing local artifact files."""
⋮----
root_path = Path(root)
⋮----
def initialize_schema(self) -> None
⋮----
def load_runtime(self, runtime_key: str, starting_cash: float) -> PersistedRuntime
⋮----
is_new = not self.state_store.path.exists()
state = self.state_store.load(starting_cash)
model: ModelBlob | None = None
⋮----
payload = self.model_path.read_bytes()
model = ModelBlob(
⋮----
def commit_step(self, runtime_key: str, commit: RuntimeStepCommit) -> CommitOutcome
⋮----
current = self.state_store.load(commit.state.cash)
⋮----
temp = self.model_path.with_suffix(".tmp")
⋮----
state = commit.state
⋮----
regimes = set(self.list_regimes(""))
⋮----
def load_trade_performance(self, runtime_key: str) -> TradePerformanceMetrics
⋮----
weights = resolved_portfolio_allocations(runtime_keys, allocations)
⋮----
allocation_by_symbol = {
⋮----
def list_burnin_snapshots(self, runtime_key: str) -> tuple[BurnInSnapshot, ...]
⋮----
def list_regimes(self, runtime_key: str) -> tuple[str, ...]
⋮----
def load_shadow_quality(self, runtime_key: str) -> ShadowQualityComparison
⋮----
payloads = []
⋮----
record = json.loads(line)
⋮----
payload = record.get("payload")
⋮----
def load_river_v2_forward_quality(self, runtime_key: str) -> RiverV2ForwardComparison
⋮----
"""Read-only forward evidence from committed paper audit observations."""
⋮----
def save_runtime_status(self, runtime_key: str, status: HostedRuntimeStatus) -> None
⋮----
def load_runtime_status(self, runtime_key: str) -> HostedRuntimeStatus | None
⋮----
def record_scheduler_delivery(self, delivery: SchedulerDelivery) -> None
⋮----
deliveries: list[SchedulerDelivery] = []
⋮----
payload = json.loads(line)
```

## File: ai_trading/generation_progress.py
```python
@dataclass(frozen=True)
class GenerationProgress
⋮----
score_delta: float
improved: bool
current_generation: int
previous_generation: int
⋮----
delta = float(current.portfolio_score - previous.portfolio_score)
```

## File: ai_trading/generation_rollback.py
```python
@dataclass(frozen=True)
class GenerationRollbackResult
⋮----
restored: GenerationSnapshot
active_experts: tuple[str, ...]
⋮----
previous = generations.previous()
records = pool.load()
restored_names = set(previous.active_experts)
⋮----
updated: dict[str, ExpertRecord] = {}
⋮----
status = "active" if name in restored_names else (
```

## File: ai_trading/generations.py
```python
@dataclass(frozen=True)
class LineageRecord
⋮----
expert: str
parent: str | None
generation: int
created_at_utc: str
⋮----
@dataclass(frozen=True)
class GenerationSnapshot
⋮----
active_experts: tuple[str, ...]
portfolio_score: float
⋮----
rolled_back: bool = False
⋮----
class GenerationStore
⋮----
def load_lineage(self) -> dict[str, LineageRecord]
⋮----
payload = json.loads(self.lineage_path.read_text(encoding="utf-8"))
⋮----
def add_lineage(self, expert: str, parent: str | None, generation: int) -> LineageRecord
⋮----
data = self.load_lineage()
record = LineageRecord(
⋮----
temp = self.lineage_path.with_suffix(".tmp")
⋮----
def snapshots(self) -> list[GenerationSnapshot]
⋮----
snapshots: list[GenerationSnapshot] = []
⋮----
payload = json.loads(line)
⋮----
def current_generation(self) -> int
⋮----
snapshots = self.snapshots()
⋮----
def snapshot(self, active_experts: list[str], portfolio_score: float) -> GenerationSnapshot
⋮----
record = GenerationSnapshot(
⋮----
def previous(self) -> GenerationSnapshot
```

## File: ai_trading/global_allocator.py
```python
@dataclass(frozen=True)
class GlobalAllocatorConfig
⋮----
cvar_alpha: float = 0.95
max_cvar: float = 0.03
max_asset_weight: float = 0.40
max_expert_weight: float = 0.25
max_turnover: float = 0.30
target_gross_exposure: float = 1.0
cost_penalty: float = 1.0
turnover_penalty: float = 0.25
⋮----
def __post_init__(self) -> None
⋮----
@dataclass(frozen=True)
class GlobalAllocationReport
⋮----
weights: pd.Series
cvar: float
expected_return: float
turnover: float
estimated_cost: float
approved: bool
reasons: tuple[str, ...]
⋮----
clean = returns.astype(float).dropna()
⋮----
cutoff = float(clean.quantile(1.0 - alpha))
tail = clean[clean <= cutoff]
⋮----
positive = scores.clip(lower=0.0).astype(float)
⋮----
result = pd.Series(0.0, index=positive.index, dtype=float)
free = list(positive.index)
remaining = float(target)
⋮----
base = positive.loc[free]
total = float(base.sum())
proposal = (
over = proposal[proposal > cap + 1e-12]
⋮----
config = config or GlobalAllocatorConfig()
⋮----
columns = opportunity_returns.columns
alpha = expected_alpha.reindex(columns).fillna(0.0).astype(float)
q = quality.reindex(columns).fillna(0.0).clip(lower=0.0).astype(float)
⋮----
vol = opportunity_returns.astype(float).std(ddof=1).replace(0.0, np.nan)
raw_score = (alpha.clip(lower=0.0) * q / vol).replace([np.inf, -np.inf], np.nan).fillna(0.0)
weights = _normalize_capped(
⋮----
# Enforce asset-level concentration if columns use "asset|expert|regime".
asset_totals: dict[str, float] = {}
⋮----
asset = str(key).split("|", 1)[0]
⋮----
scale = config.max_asset_weight / total
⋮----
# Do not renormalize upward after asset caps: doing so could violate
# concentration constraints. A constrained portfolio may intentionally
# run below target gross exposure.
gross = float(weights.sum())
⋮----
current = (
turnover = float((weights - current).abs().sum())
estimated_cost = turnover * transaction_cost_bps / 10_000.0
⋮----
portfolio_returns = opportunity_returns.fillna(0.0).mul(weights, axis=1).sum(axis=1)
cvar = expected_shortfall(portfolio_returns, alpha=config.cvar_alpha)
expected_return = float(portfolio_returns.mean())
⋮----
reasons: list[str] = []
```

## File: ai_trading/global_selection.py
```python
@dataclass(frozen=True)
class GlobalGenerationDecision
⋮----
accept: bool
reason: str
```

## File: ai_trading/governor_state_store.py
```python
@dataclass(frozen=True)
class GovernorState
⋮----
verdict: str = "TRADE"
reason: str = "initial state"
consecutive_halts: int = 0
⋮----
class GovernorStateStore
⋮----
def __init__(self, path: str | Path = "artifacts/risk_governor_state.json") -> None
⋮----
def load(self) -> GovernorState
⋮----
payload = json.loads(self.path.read_text(encoding="utf-8"))
⋮----
def save(self, state: GovernorState) -> None
⋮----
temp = self.path.with_suffix(".tmp")
```

## File: ai_trading/guardrails.py
```python
@dataclass(frozen=True)
class HealthPolicy
⋮----
min_sharpe: float = 0.0
max_drawdown: float = 0.15
rollback_on_drift: bool = True
⋮----
@dataclass(frozen=True)
class HealthDecision
⋮----
healthy: bool
rollback: bool
reason: str
⋮----
policy = policy or HealthPolicy()
⋮----
restored = registry.rollback()
```

## File: ai_trading/health_server.py
```python
class HealthHandler(BaseHTTPRequestHandler)
⋮----
heartbeat_store = HeartbeatStore("artifacts/multiasset_heartbeat.json")
⋮----
def do_GET(self) -> None
⋮----
body = prometheus_text(collect_metrics()).encode("utf-8")
⋮----
control = read_control_plane()
heartbeat = self.heartbeat_store.load()
stale = heartbeat_is_stale(heartbeat)
⋮----
payload = {
⋮----
status = 200 if payload["ready"] else 503
body = json.dumps(payload, sort_keys=True).encode("utf-8")
⋮----
def log_message(self, format: str, *args) -> None
⋮----
class HealthServer
⋮----
def __init__(self, host: str = "127.0.0.1", port: int = 8765) -> None
⋮----
def start(self) -> None
⋮----
def stop(self) -> None
```

## File: ai_trading/hosted_runtime.py
```python
@dataclass(frozen=True)
class HostedPaperSettings
⋮----
enabled: bool = False
external_scheduler: bool = False
symbol: str = "GC=F"
period: str = "1y"
interval: str = "1d"
poll_seconds: float = 60.0
shadow_challenger: bool = False
mtf_period: str = "1mo"
⋮----
@property
    def runtime_key(self) -> str
⋮----
@classmethod
    def from_env(cls) -> HostedPaperSettings
⋮----
enabled = os.getenv("AI_TRADING_HOSTED_PAPER", "0").strip().lower() in {
external_scheduler = os.getenv(
symbol = os.getenv("AI_TRADING_HOSTED_SYMBOL", "GC=F").strip() or "GC=F"
period = os.getenv("AI_TRADING_HOSTED_PERIOD", "1y").strip() or "1y"
interval = os.getenv("AI_TRADING_HOSTED_INTERVAL", "1d").strip() or "1d"
poll_seconds = float(os.getenv("AI_TRADING_HOSTED_POLL_SECONDS", "60"))
mtf_period = os.getenv("AI_TRADING_MTF_PERIOD", "1mo").strip() or "1mo"
shadow_challenger = os.getenv(
⋮----
def _now_utc() -> str
⋮----
backend = persistence or build_paper_persistence()
runtime = PaperAutonomousRuntime(
⋮----
orchestrator = AutonomousPaperOrchestrator(runtime=runtime)
⋮----
def report_iteration(result: OrchestrationResult) -> None
⋮----
step = result.runtime
⋮----
scheduler = PaperScheduler(
⋮----
current = backend.load_runtime_status(settings.runtime_key) or HostedRuntimeStatus(
⋮----
except Exception as status_exc:  # noqa: BLE001 - best-effort failure reporting boundary
⋮----
effective_settings = settings or HostedPaperSettings.from_env()
⋮----
thread = Thread(
```

## File: ai_trading/kronos_research.py
```python
"""Opt-in, offline Kronos challenger evaluation. Never routes or approves orders."""
⋮----
class ForecastPredictor(Protocol)
⋮----
def predict(self, **kwargs: object) -> pd.DataFrame: ...
⋮----
@dataclass(frozen=True)
class ResearchConfig
⋮----
lookback: int = 256
horizon_bars: int = 9
max_windows: int = 40
threshold_bps: float = 5.0
transaction_cost_bps: float = 2.0
slippage_bps: float = 1.0
sample_count: int = 3
river_min_confidence: float = 0.56
⋮----
def __post_init__(self) -> None
⋮----
def validate_market(frame: pd.DataFrame) -> pd.DataFrame
⋮----
"""Reject malformed time series rather than silently changing signal ordering."""
⋮----
required = ("Open", "High", "Low", "Close")
⋮----
result = frame.copy()
⋮----
columns = (*required, "Volume")
result = result.loc[:, columns].apply(pd.to_numeric, errors="raise")
⋮----
def _side(return_fraction: float, threshold_bps: float) -> int
⋮----
def _net_return(side: int, forward_return: float, config: ResearchConfig) -> float
⋮----
round_trip_cost = 2 * (config.transaction_cost_bps + config.slippage_bps) / 10_000
⋮----
def _bootstrap_lower(values: list[float], *, seed: int = 42) -> float | None
⋮----
generator = np.random.default_rng(seed)
samples = np.asarray(values, dtype=float)
means = np.mean(generator.choice(samples, size=(2000, len(samples))), axis=1)
⋮----
"""Train on matured labels only, then predict on each shared signal bar.

    This uses a corrected *research-only* three-class River model, not the
    persisted production v1 binary model. Predictions share the exact entry
    and exit with Kronos, but no forward outcome is available at inference.
    """
⋮----
model = RiverMulticlassDirectionModel()
features = make_features(market)
labels = make_labels(
results: dict[int, tuple[int, float, int]] = {}
learned_through = -1
⋮----
matured_last = signal_pos - config.horizon_bars
⋮----
row = features.iloc[index]
label = labels.iloc[index]
⋮----
learned_through = matured_last
⋮----
signal_features = features.iloc[signal_pos]
⋮----
prediction = model.predict_one(signal_features)
side = (
⋮----
"""Evaluate non-overlapping realized windows; never send future OHLCV to Kronos."""
market = validate_market(market)
end_signal = len(market) - config.horizon_bars - 1
⋮----
# Spread bounded, non-overlapping windows over the available history,
# rather than selecting only the most recent few hours of a long sample.
candidates = list(range(config.lookback - 1, end_signal + 1, config.horizon_bars))
⋮----
signal_positions = candidates
⋮----
selected = np.linspace(0, len(candidates) - 1, config.max_windows, dtype=int)
signal_positions = [candidates[int(i)] for i in selected]
river_predictions = _river_predictions(market, signal_positions, config)
observations: list[dict[str, object]] = []
forecast_columns = {"Open": "open", "High": "high", "Low": "low", "Close": "close", "Volume": "volume"}
⋮----
history = market.iloc[signal_pos + 1 - config.lookback : signal_pos + 1]
step = history.index.to_series().diff().dropna().median()
future_times = pd.date_range(
observed_times = market.index[signal_pos + 1 : signal_pos + config.horizon_bars + 1]
⋮----
continue  # Market closure or missing bars: do not infer unseen timestamps.
forecast = predictor.predict(
⋮----
predicted_close = float(forecast["close"].iloc[-1])
⋮----
signal_close = float(history["Close"].iloc[-1])
entry_open = float(market["Open"].iloc[signal_pos + 1])
future_close = float(market["Close"].iloc[signal_pos + config.horizon_bars])
predicted_return = predicted_close / signal_close - 1
realized_return = future_close / entry_open - 1
kronos_side = _side(predicted_return, config.threshold_bps)
momentum_return = signal_close / float(history["Close"].iloc[-1 - config.horizon_bars]) - 1
baseline_side = _side(momentum_return, config.threshold_bps)
kronos_net = _net_return(kronos_side, realized_return, config)
baseline_net = _net_return(baseline_side, realized_return, config)
⋮----
river_net = _net_return(river_side, realized_return, config)
⋮----
kronos = [float(item["kronos_net_return"]) for item in observations]
baseline = [float(item["momentum_net_return"]) for item in observations]
alpha = [k - b for k, b in zip(kronos, baseline, strict=True)]
river = [float(item["river_net_return"]) for item in observations]
river_alpha = [k - r for k, r in zip(kronos, river, strict=True)]
directional = [item for item in observations if item["kronos_side"] != 0]
mean_lower = _bootstrap_lower(kronos)
alpha_lower = _bootstrap_lower(alpha)
river_alpha_lower = _bootstrap_lower(river_alpha)
summary = {
⋮----
def load_predictor(source_dir: Path, model_size: str, device: str) -> ForecastPredictor
⋮----
"""Load the original upstream implementation, never a substitute predictor."""
source_dir = source_dir.expanduser().resolve()
⋮----
from model import Kronos, KronosPredictor, KronosTokenizer  # type: ignore[import-not-found]
⋮----
tokenizer_id = "NeoQuasar/Kronos-Tokenizer-2k" if model_size == "mini" else "NeoQuasar/Kronos-Tokenizer-base"
tokenizer = KronosTokenizer.from_pretrained(tokenizer_id)
model = Kronos.from_pretrained(f"NeoQuasar/Kronos-{model_size}")
⋮----
def main() -> None
⋮----
parser = argparse.ArgumentParser(description="Offline Kronos paper-only quality research")
⋮----
args = parser.parse_args()
⋮----
config = ResearchConfig(
⋮----
frame = pd.read_csv(args.csv)
⋮----
market = frame.set_index("timestamp")
⋮----
market = load_history(args.symbol, period=args.period, interval=args.interval)
predictor = load_predictor(args.kronos_source, args.model_size, args.device)
result = evaluate_walk_forward(market, predictor, config)
```

## File: ai_trading/lifecycle_log.py
```python
@dataclass(frozen=True)
class LifecycleEvent
⋮----
event: str
version: str
model_name: str
reason: str
failure_type: str
processed_bar: int
artifact_sha256: str | None
artifact_path: str | None
metadata: dict[str, Any]
created_at_utc: str
⋮----
class LifecycleEventLog
⋮----
def __init__(self, path: str | Path = "artifacts/model_lifecycle.jsonl") -> None
⋮----
artifact_hash = (
record = LifecycleEvent(
⋮----
def list(self) -> list[LifecycleEvent]
⋮----
records: list[LifecycleEvent] = []
⋮----
payload = json.loads(line)
⋮----
def sha256_file(path: str | Path) -> str
⋮----
digest = hashlib.sha256()
```

## File: ai_trading/maintenance.py
```python
@dataclass(frozen=True)
class MaintenanceState
⋮----
enabled: bool = False
reason: str = ""
⋮----
class MaintenanceStore
⋮----
def __init__(self, path: str | Path = "artifacts/maintenance.json") -> None
⋮----
def load(self) -> MaintenanceState
⋮----
def save(self, state: MaintenanceState) -> None
⋮----
temp = self.path.with_suffix(".tmp")
```

## File: ai_trading/marginal_alpha.py
```python
@dataclass(frozen=True)
class MarginalAlphaReport
⋮----
marginal_return: float
marginal_sharpe: float
marginal_drawdown: float
correlation_to_portfolio: float
improves_portfolio: bool
⋮----
frame = pd.concat(
⋮----
base_equity = (1.0 + frame["portfolio"]).cumprod() * 100_000.0
blended_returns = (
blended_equity = (1.0 + blended_returns).cumprod() * 100_000.0
⋮----
base = compute_metrics(base_equity)
blended = compute_metrics(blended_equity)
corr = float(frame["portfolio"].corr(frame["candidate"]))
⋮----
corr = 0.0
⋮----
marginal_return = blended.total_return - base.total_return
marginal_sharpe = blended.sharpe - base.sharpe
marginal_drawdown = blended.max_drawdown - base.max_drawdown
⋮----
improves = (
```

## File: ai_trading/market_freshness.py
```python
_PROVIDER_GAP_ERRORS = {
⋮----
def _utc_now(now: datetime | None) -> datetime
⋮----
current = now or datetime.now(UTC)
⋮----
def market_session_open(symbol: str, *, now: datetime | None = None) -> bool | None
⋮----
"""Return the expected weekly session state for supported paper markets.

    This intentionally models regular weekly sessions only. Exchange holidays are
    not guessed; unsupported symbols return None instead of a false precision.
    """
⋮----
current = _utc_now(now)
⋮----
local = current.astimezone(ZoneInfo("Europe/Berlin"))
⋮----
local = current.astimezone(ZoneInfo("America/New_York"))
weekday = local.weekday()
local_time = local.time().replace(tzinfo=None)
⋮----
session_open = market_session_open(symbol, now=now)
⋮----
engine_status = str(status_snapshot.get("engine_status") or "OFF").upper()
⋮----
"""Only expose a fresh, completed PAPER decision; never imply live trade advice."""
snapshot: dict[str, object] = {
⋮----
units = {"m": 60, "h": 3600, "d": 86400}
match = fullmatch(r"([1-9][0-9]*)(m|h|d)", status.interval)
⋮----
timestamp = datetime.fromisoformat(status.last_cycle_timestamp)
⋮----
age_seconds = (_utc_now(now) - timestamp.astimezone(UTC)).total_seconds()
⋮----
max_age = max(3 * int(match.group(1)) * units[match.group(2)], 300)
```

## File: ai_trading/meta_router.py
```python
@dataclass(frozen=True)
class MetaContext
⋮----
symbol: str
regime: str
volatility_bucket: str
drawdown_bucket: str
⋮----
@dataclass(frozen=True)
class ModelContextStats
⋮----
wins: int = 0
losses: int = 0
cumulative_edge: float = 0.0
⋮----
@property
    def observations(self) -> int
⋮----
@property
    def success_rate(self) -> float
⋮----
@property
    def mean_edge(self) -> float
⋮----
@property
    def score(self) -> float
⋮----
@dataclass(frozen=True)
class RoutedPrediction
⋮----
prediction: Prediction
weights: dict[str, float]
⋮----
def context_key(context: MetaContext) -> str
⋮----
raw = {
total = sum(raw.values())
weights = {name: value / total for name, value in raw.items()}
⋮----
aggregate = {-1: 0.0, 0: 0.0, 1: 0.0}
⋮----
weight = weights[name]
⋮----
side = max(aggregate, key=aggregate.get)
```

## File: ai_trading/meta_store.py
```python
class MetaRouterStore
⋮----
def __init__(self, path: str | Path = "artifacts/meta_router.json") -> None
⋮----
def load(self) -> dict[str, dict[str, ModelContextStats]]
⋮----
payload = json.loads(self.path.read_text(encoding="utf-8"))
⋮----
def save(self, data: dict[str, dict[str, ModelContextStats]]) -> None
⋮----
temp = self.path.with_suffix(".tmp")
⋮----
data = self.load()
key = context_key(context)
models = data.setdefault(key, {})
current = models.get(model_name, ModelContextStats())
updated = ModelContextStats(
⋮----
def scores(self, context: MetaContext) -> dict[str, float]
⋮----
models = data.get(context_key(context), {})
```

## File: ai_trading/metrics.py
```python
@dataclass(frozen=True)
class MetricsSnapshot
⋮----
governor_trade: int
governor_halt: int
heartbeat_stale: int
crisis_level: int
consecutive_halts: int
supervisor_running: int
supervisor_restarting: int
supervisor_maintenance: int
supervisor_halted: int
supervisor_restarts: int
promotion_total: int
promotion_rejected_total: int
rollback_total: int
quarantine_total: int
recovery_attempt_total: int
recovery_success_total: int
recovery_failure_total: int
recovery_fallback_depth: int
recovery_degraded: int
resilience_level: int
resilience_unstable: int
resilience_oscillations: int
reliability_score: float
reliability_normal_ratio: float
reliability_halt_ratio: float
⋮----
heartbeat_store = heartbeat_store or HeartbeatStore(
governor_store = governor_store or GovernorStateStore()
supervisor_store = supervisor_store or SupervisorStateStore()
lifecycle_log = lifecycle_log or LifecycleEventLog()
quarantine_store = quarantine_store or ModelQuarantineStore()
resilience_store = resilience_store or ResilienceStateStore()
control = read_control_plane(governor_store=governor_store)
governor = governor_store.load()
supervisor = supervisor_store.load()
lifecycle_events = lifecycle_log.list()
quarantine_records = quarantine_store.load()
recovery_health = evaluate_recovery_health(lifecycle_log)
resilience = resilience_store.load()
reliability = evaluate_reliability(lifecycle_log, resilience)
resilience_stability = evaluate_resilience_stability(
⋮----
crisis_levels = {
resilience_levels = {
⋮----
def prometheus_text(snapshot: MetricsSnapshot) -> str
```

## File: ai_trading/model_blend.py
```python
@dataclass(frozen=True)
class BlendComponent
⋮----
name: str
prediction: Prediction
quality_score: float
⋮----
aggregate = {-1: 0.0, 0: 0.0, 1: 0.0}
total_weight = 0.0
⋮----
weight = max(min_quality, float(component.quality_score))
⋮----
aggregate = {side: value / total_weight for side, value in aggregate.items()}
side = max(aggregate, key=aggregate.get)
```

## File: ai_trading/model_codec.py
```python
MODEL_FORMAT = "joblib-river-v1"
MODEL_VERSION = 1
⋮----
def serialize_model(model: RiverDirectionModel) -> ModelBlob
⋮----
# Production persistence must never silently accept research v2 subclasses.
⋮----
buffer = BytesIO()
⋮----
payload = buffer.getvalue()
⋮----
def deserialize_model(blob: ModelBlob) -> RiverDirectionModel
⋮----
model = joblib.load(BytesIO(blob.payload))
```

## File: ai_trading/model_quality.py
```python
@dataclass(frozen=True)
class ModelQuality
⋮----
score: float
accuracy: float
brier: float
directional_edge: float
observations: int
⋮----
frame = pd.concat(
⋮----
pred = frame["pred"].astype(int)
label = frame["label"].astype(int)
confidence = frame["confidence"].astype(float).clip(0.0, 1.0)
⋮----
correct = (pred == label).astype(float)
accuracy = float(correct.mean())
⋮----
# Treat confidence as probability assigned to the predicted class.
brier = float(((confidence - correct) ** 2).mean())
⋮----
active = frame[pred != 0]
⋮----
edge = 0.0
⋮----
edge = float((active["pred"].astype(int) == active["label"].astype(int)).mean() - 0.5)
⋮----
score = (
```

## File: ai_trading/model_quarantine.py
```python
@dataclass(frozen=True)
class QuarantinePolicy
⋮----
failures_before_quarantine: int = 2
base_backoff_bars: int = 20
max_backoff_bars: int = 640
⋮----
@dataclass(frozen=True)
class QuarantineRecord
⋮----
version: str
failures: int = 0
quarantined: bool = False
next_eligible_bar: int = 0
last_reason: str = ""
failure_type: str = ""
⋮----
class ModelQuarantineStore
⋮----
def __init__(self, path: str | Path = "artifacts/model_quarantine.json") -> None
⋮----
def load(self) -> dict[str, QuarantineRecord]
⋮----
payload = json.loads(self.path.read_text(encoding="utf-8"))
⋮----
def save(self, records: dict[str, QuarantineRecord]) -> None
⋮----
temp = self.path.with_suffix(".tmp")
⋮----
policy = policy or QuarantinePolicy()
records = self.load()
previous = records.get(version, QuarantineRecord(version=version))
failures = previous.failures + 1
exponent = max(0, failures - 1)
backoff = min(
record = QuarantineRecord(
⋮----
def record_success(self, version: str) -> QuarantineRecord
⋮----
record = QuarantineRecord(version=version)
⋮----
def eligible(self, version: str, *, processed_bar: int) -> bool
⋮----
record = self.load().get(version)
⋮----
def release(self, version: str) -> QuarantineRecord
```

## File: ai_trading/model.py
```python
@dataclass(frozen=True)
class Prediction
⋮----
side: int
confidence: float
probabilities: dict[int, float]
⋮----
class OnlineDirectionModel
⋮----
"""Incrementally trainable three-class direction model: short/flat/long."""
⋮----
classes = np.array([-1, 0, 1], dtype=int)
⋮----
def __init__(self, random_state: int = 42) -> None
⋮----
def fit(self, x: pd.DataFrame, y: pd.Series) -> None
⋮----
x2 = x.loc[:, FEATURES].dropna()
y2 = y.reindex(x2.index).dropna().astype(int)
x2 = x2.loc[y2.index]
⋮----
def predict_one(self, row: pd.Series) -> Prediction
⋮----
x = pd.DataFrame([row.loc[FEATURES].astype(float).to_dict()])
proba = self.pipeline.predict_proba(x)[0]
model = self.pipeline.named_steps["model"]
mapping = {int(cls): float(p) for cls, p in zip(model.classes_, proba, strict=True)}
side = max(mapping, key=mapping.get)
```

## File: ai_trading/mtf_parameter_benchmark.py
```python
_MIN_ACTIVE_PREDICTIONS = 20
_MIN_ACTIVE_PRECISION = 0.50
⋮----
@dataclass(frozen=True)
class MTFBenchmarkConfig
⋮----
horizon_bars: int
minimum_threshold: float
atr_multiplier: float
max_train_rows: int
min_confidence: float
⋮----
def __post_init__(self) -> None
⋮----
@property
    def horizon_minutes(self) -> int
⋮----
@property
    def name(self) -> str
⋮----
threshold_bps = round(self.minimum_threshold * 10_000)
⋮----
@dataclass(frozen=True)
class MarketBenchmarkResult
⋮----
symbol: str
config_name: str
folds: int
observations: int
directional_observations: int
long_labels: int
flat_labels: int
short_labels: int
accuracy: float
macro_recall: float
brier: float
directional_accuracy: float
directional_edge: float
active_predictions: int
active_precision: float
quality_score: float
selection_score: float
directional_gate_passed: bool
⋮----
@dataclass(frozen=True)
class AggregateBenchmarkResult
⋮----
config: MTFBenchmarkConfig
markets: tuple[MarketBenchmarkResult, ...]
mean_selection_score: float
stability_penalty: float
aggregate_score: float
total_observations: int
total_directional_observations: int
markets_passing_directional_gate: int
⋮----
def default_benchmark_grid() -> tuple[MTFBenchmarkConfig, ...]
⋮----
"""Refined grid after the first coarse 10m/15m/30m benchmark.

    The first run showed 30m ahead of 15m/10m, while ATR multipliers were
    largely masked by the 10bp threshold floor. This grid therefore expands
    horizon and confidence while testing a lower threshold floor.
    """
⋮----
def btc_focused_benchmark_grid() -> tuple[MTFBenchmarkConfig, ...]
⋮----
"""Focused search for BTC after the shared grid failed its directional gate."""
⋮----
"""Choose the strongest gate-passing configuration independently per market."""
⋮----
symbols = sorted(
selections: dict[str, dict[str, object] | None] = {}
⋮----
candidates: list[tuple[MarketBenchmarkResult, MTFBenchmarkConfig]] = []
⋮----
def _macro_recall(predicted: pd.Series, realized: pd.Series) -> float
⋮----
recalls: list[float] = []
⋮----
mask = realized == label
⋮----
active_edge = max(0.0, min(1.0, (active_precision - 0.5) * 2.0))
active_evidence = min(1.0, active_predictions / 20.0)
⋮----
required = min_train_rows + folds * test_window_bars
⋮----
start = len(usable) - folds * test_window_bars
⋮----
features = make_multi_timeframe_challenger_features(market)
labels = make_volatility_adaptive_labels(
usable = features.dropna().index.intersection(labels.dropna().index)
windows = _fold_test_windows(
⋮----
market_positions = {timestamp: pos for pos, timestamp in enumerate(market.index)}
predicted_sides: list[int] = []
confidences: list[float] = []
realized_labels: list[int] = []
⋮----
completed_folds = 0
⋮----
first_test = test_idx[0]
first_test_pos = market_positions[first_test]
max_train_pos = first_test_pos - config.horizon_bars
train_candidates = [
⋮----
train_idx = train_candidates[-config.max_train_rows :]
⋮----
model = EnsembleDirectionModel(
⋮----
row = features.loc[signal_idx, MTF_CHALLENGER_FEATURES]
prediction = model.predict_one(row, detect_regime(row))
label = labels.loc[signal_idx]
⋮----
effective_side = (
⋮----
index = pd.RangeIndex(len(realized_labels))
predicted = pd.Series(predicted_sides, index=index, dtype="int64")
confidence = pd.Series(confidences, index=index, dtype="float64")
realized = pd.Series(realized_labels, index=index, dtype="int64")
⋮----
quality = evaluate_model_quality(predicted, confidence, realized)
directional_mask = realized != 0
directional_observations = int(directional_mask.sum())
directional_accuracy = (
active_mask = predicted != 0
active_predictions = int(active_mask.sum())
active_precision = (
macro_recall = _macro_recall(predicted, realized)
selection_score = _selection_score(
directional_gate_passed = (
⋮----
grid = tuple(configs or default_benchmark_grid())
⋮----
results: list[AggregateBenchmarkResult] = []
⋮----
market_results = tuple(
scores = [row.selection_score for row in market_results]
stability_penalty = pstdev(scores) if len(scores) > 1 else 0.0
mean_score = fmean(scores)
⋮----
def benchmark_payload(results: tuple[AggregateBenchmarkResult, ...]) -> dict[str, object]
⋮----
payload = benchmark_payload(results)
json_target = Path(json_path)
markdown_target = Path(markdown_path)
⋮----
selections = market_selections(results)
lines = [
⋮----
def main() -> None
⋮----
parser = argparse.ArgumentParser(description="Run MTF parameter benchmark")
⋮----
args = parser.parse_args()
⋮----
symbols = tuple(part.strip() for part in args.symbols.split(",") if part.strip())
⋮----
markets = {
configs = (
results = run_parameter_benchmark(
```

## File: ai_trading/mtf_shadow_challenger.py
```python
@dataclass(frozen=True)
class MultiTimeframeShadowResult
⋮----
config_name: str
prediction: Prediction
raw_side: int
min_confidence: float
regime: str
signal_time: str
execution_time: str
training_rows: int
training_end: str
realized_label: int
horizon_bars: int
horizon_minutes: int
timeframes: tuple[str, ...]
threshold_at_signal: float
minimum_threshold: float
atr_multiplier: float
feature_count: int
⋮----
"""Select the newest shadow target whose horizon is observable now.

    The chosen target is delayed relative to the current production target, so
    its full forward outcome is known without using information unavailable at
    the time the shadow prediction would have been made.
    """
⋮----
current_pos = int(market.index.get_loc(current_execution_idx))
max_execution_pos = current_pos - (horizon_bars - 1)
⋮----
candidate = None
⋮----
execution_pos = int(market.index.get_loc(execution_idx))
⋮----
candidate = execution_idx
⋮----
"""Evaluate a 5m/15m/1h/4h ensemble without controlling execution."""
⋮----
full_execution_pos = int(market.index.get_loc(execution_idx))
⋮----
window_start = max(
window_stop = min(
market = market.iloc[window_start:window_stop]
authoritative_features = authoritative_features.reindex(market.index)
⋮----
signal_pos = execution_pos - 1
signal_idx = market.index[signal_pos]
⋮----
mtf_features = make_multi_timeframe_challenger_features(market)
⋮----
signal_row = mtf_features.loc[signal_idx, MTF_CHALLENGER_FEATURES]
⋮----
labels = make_volatility_adaptive_labels(
threshold = adaptive_return_threshold(
⋮----
last_train_pos = signal_pos - horizon_bars
⋮----
allowed = set(market.index[: last_train_pos + 1])
valid_feature_rows = mtf_features.loc[:, MTF_CHALLENGER_FEATURES].dropna().index
labeled_rows = labels.dropna().index
train_idx = [
⋮----
train_idx = train_idx[-max_train_rows:]
⋮----
realized = labels.get(signal_idx)
threshold_at_signal = threshold.get(signal_idx)
⋮----
model = EnsembleDirectionModel(
⋮----
regime = detect_regime(signal_row)
raw_prediction = model.predict_one(signal_row, regime)
effective_side = (
prediction = Prediction(
```

## File: ai_trading/mtf_shadow_config.py
```python
@dataclass(frozen=True)
class ValidatedMTFShadowConfig
⋮----
"""Benchmark-validated, research-only MTF shadow configuration."""
⋮----
symbol: str
config_name: str
horizon_bars: int
minimum_threshold: float
atr_multiplier: float
max_train_rows: int
min_confidence: float
min_train_rows: int = 500
feature_warmup_rows: int = 600
⋮----
@property
    def horizon_minutes(self) -> int
⋮----
def as_dict(self) -> dict[str, object]
⋮----
_VALIDATED_CONFIGS: dict[str, ValidatedMTFShadowConfig] = {
⋮----
"""Return a benchmark-validated MTF config, or None when none passed."""
```

## File: ai_trading/mtf_shadow_quality.py
```python
@dataclass(frozen=True)
class MultiTimeframeShadowQuality
⋮----
observations: int
river: ModelQuality
challenger: ModelQuality
long_labels: int = 0
flat_labels: int = 0
short_labels: int = 0
⋮----
@property
    def score_delta(self) -> float
⋮----
@property
    def directional_observations(self) -> int
⋮----
@property
    def directional_rate(self) -> float
⋮----
def _empty_quality() -> ModelQuality
⋮----
"""Compare delayed MTF predictions with River at the same execution time."""
⋮----
river_by_execution: dict[str, tuple[int, float]] = {}
shadow_by_execution: dict[str, tuple[int, float, int]] = {}
⋮----
execution_time = payload.get("execution_time")
prediction = payload.get("prediction")
⋮----
side = int(prediction["side"])
confidence = float(prediction["confidence"])
⋮----
shadow = payload.get("mtf_shadow_challenger")
⋮----
shadow_execution = shadow.get("execution_time")
shadow_prediction = shadow.get("prediction")
realized = shadow.get("realized_label")
⋮----
side = int(shadow_prediction["side"])
confidence = float(shadow_prediction["confidence"])
label = int(realized)
⋮----
river_sides: list[int] = []
river_confidences: list[float] = []
challenger_sides: list[int] = []
challenger_confidences: list[float] = []
labels: list[int] = []
⋮----
river = river_by_execution.get(execution_time)
⋮----
observations = len(labels)
⋮----
empty = _empty_quality()
⋮----
index = pd.RangeIndex(observations)
realized = pd.Series(labels, index=index, dtype="int64")
river = evaluate_model_quality(
challenger = evaluate_model_quality(
```

## File: ai_trading/multi_market.py
```python
_NORMALIZED_RUNTIME_CASH = 100_000.0
⋮----
@dataclass(frozen=True)
class MarketSpec
⋮----
symbol: str
label: str
allocation: float
⋮----
def __post_init__(self) -> None
⋮----
def _validate_market_bundle(markets: tuple[MarketSpec, ...]) -> None
⋮----
symbols = tuple(market.symbol for market in markets)
⋮----
total_allocation = sum(market.allocation for market in markets)
⋮----
DEFAULT_MARKETS: tuple[MarketSpec, ...] = (
⋮----
def configured_markets_from_env() -> tuple[MarketSpec, ...]
⋮----
raw = os.getenv("AI_TRADING_MARKETS", "").strip()
⋮----
symbols = tuple(part.strip() for part in raw.split(","))
⋮----
known = {spec.symbol: spec for spec in DEFAULT_MARKETS}
⋮----
weight = 1.0 / len(symbols)
markets = tuple(
⋮----
backend = persistence
⋮----
backend = build_paper_persistence()
except Exception as exc:  # noqa: BLE001 - sanitize provider failures
⋮----
processed = 0
remaining_backlog = False
processed_bars = 0
last_processed: str | None = None
mtf_evaluated = False
failures: list[tuple[str, str]] = []
⋮----
def run_market(market: MarketSpec)
⋮----
futures = {
⋮----
market = futures[future]
⋮----
result = future.result()
⋮----
except Exception:  # noqa: BLE001 - isolate and sanitize one market
⋮----
remaining_backlog = remaining_backlog or result.remaining_backlog
mtf_evaluated = mtf_evaluated or result.mtf_evaluated
⋮----
last_processed = (
⋮----
# Record which known market failed without exposing provider exception text.
known_symbols = {market.symbol for market in DEFAULT_MARKETS}
⋮----
failure_codes = {code for _, code in failures}
code = (
⋮----
reason = f"processed {processed} bar(s) across {len(markets) - len(failures)} market(s)"
⋮----
market_rows: list[dict[str, object]] = []
portfolio_equity = 0.0
portfolio_equity_complete = True
healthy_markets = 0
running_markets = 0
stale_markets = 0
error_markets = 0
alert_markets = 0
closed_markets = 0
catching_up_markets = 0
provider_gap_markets = 0
runtime_keys = tuple(
portfolio_performance = empty_performance_payload()
load_portfolio_performance = getattr(
⋮----
portfolio_performance = performance_payload(
except Exception:  # noqa: BLE001 - optional observer must not break overview
⋮----
# Independent, read-only model diagnostics can run concurrently.
# Collect futures in input order to preserve stable market rows.
⋮----
overview_futures = {
⋮----
runtime_key = build_runtime_key(market.symbol, interval)
allocated_cash = portfolio_cash * market.allocation
⋮----
persisted = persistence.load_runtime(runtime_key, _NORMALIZED_RUNTIME_CASH)
normalized_equity = (
sleeve_equity = allocated_cash * normalized_equity / _NORMALIZED_RUNTIME_CASH
overview = overview_futures[market.symbol].result()
status = persistence.load_runtime_status(runtime_key)
market_reason = None
cycle_duration_seconds = None
market_mtf_evaluated = False
heartbeat_age_seconds = None
freshness = "OFF"
⋮----
market_reason = status.reason
cycle_duration_seconds = status.cycle_duration_seconds
market_mtf_evaluated = status.mtf_evaluated
status_snapshot = runtime_status_snapshot(status, now=now)
heartbeat_age_seconds = status_snapshot.get("heartbeat_age_seconds")
⋮----
session_open = None
signal_snapshot = paper_signal_snapshot(
healthy = bool(overview.get("storage_healthy"))
⋮----
engine_status = str(overview.get("engine_status") or "UNKNOWN").upper()
⋮----
except Exception:  # noqa: BLE001 - isolate one market from the dashboard
portfolio_equity_complete = False
⋮----
reported_portfolio_equity = (
reported_portfolio_pnl = (
```

## File: ai_trading/multi_timeframe_features.py
```python
MTF_CONTEXT_FEATURES = [
⋮----
MTF_CHALLENGER_FEATURES = [*CHALLENGER_FEATURES, *MTF_CONTEXT_FEATURES]
⋮----
def _infer_base_delta(index: pd.DatetimeIndex) -> pd.Timedelta
⋮----
deltas = index.to_series().diff().dropna()
deltas = deltas[deltas > pd.Timedelta(0)]
⋮----
def _resample_ohlcv(market: pd.DataFrame, rule: str) -> pd.DataFrame
⋮----
aggregated = market.resample(
⋮----
def _rsi(close: pd.Series, window: int) -> pd.Series
⋮----
delta = close.diff()
average_gain = delta.clip(lower=0.0).rolling(window).mean()
average_loss = (-delta.clip(upper=0.0)).rolling(window).mean()
relative_strength = average_gain / average_loss.replace(0.0, np.nan)
rsi = 100.0 - (100.0 / (1.0 + relative_strength))
rsi = rsi.mask((average_loss == 0.0) & (average_gain > 0.0), 100.0)
rsi = rsi.mask((average_loss == 0.0) & (average_gain == 0.0), 50.0)
⋮----
close = frame["Close"].astype(float)
returns = close.pct_change()
out = pd.DataFrame(index=frame.index)
⋮----
availability = market_index + base_delta
aligned = context.reindex(availability, method="ffill")
⋮----
"""Build leakage-safe 5m/15m/1h/4h features on the base market index.

    Higher-timeframe bars are labeled at their close and are only exposed to a
    5-minute signal row once that higher-timeframe close is available at the
    following execution boundary.
    """
⋮----
required = {"Open", "High", "Low", "Close", "Volume"}
missing = required.difference(market.columns)
⋮----
base = make_challenger_features(market).copy()
base_delta = _infer_base_delta(market.index)
⋮----
contexts = (
⋮----
resampled = _resample_ohlcv(market, rule)
context = _context_features(resampled, **settings)
aligned = _align_completed_context(market.index, context, base_delta)
⋮----
high = market["High"].astype(float)
low = market["Low"].astype(float)
close = market["Close"].astype(float)
previous_close = close.shift(1)
true_range = pd.concat(
atr_pct = true_range.rolling(atr_window).mean() / close.replace(0.0, np.nan)
⋮----
"""Label 15-minute direction on 5-minute data using a volatility floor."""
⋮----
future_return = close.shift(-horizon_bars) / close - 1.0
threshold = adaptive_return_threshold(
⋮----
labels = pd.Series(0, index=market.index, dtype="int8")
⋮----
invalid = future_return.isna() | threshold.isna()
```

## File: ai_trading/multiasset_backtest.py
```python
@dataclass(frozen=True)
class MultiAssetBacktestReport
⋮----
metrics: PerformanceMetrics
equity_curve: pd.Series
trades: int
decisions: int
rejected_rebalances: int
⋮----
class MultiAssetWalkForwardBacktester
⋮----
def run(self, markets: dict[str, pd.DataFrame]) -> MultiAssetBacktestReport
⋮----
common = None
⋮----
common = df.index if common is None else common.intersection(df.index)
⋮----
aligned = {
features = {s: make_features(df) for s, df in aligned.items()}
labels = {
closes = pd.DataFrame({s: df["Close"].astype(float) for s, df in aligned.items()})
returns = closes.pct_change()
⋮----
cash = self.risk_config.starting_cash
units = {s: 0.0 for s in aligned}
last_prices = {s: float(aligned[s]["Close"].iloc[0]) for s in aligned}
peak_equity = cash
curve: dict[pd.Timestamp, float] = {}
trades = 0
decisions = 0
rejected = 0
⋮----
purge = max(1, self.model_config.horizon_bars)
start = self.min_train_bars + purge
⋮----
test_end = min(start + self.test_window_bars, len(common) - 1)
train_end = start - purge
train_idx = common[:train_end]
test_idx = common[start:test_end]
⋮----
models: dict[str, EnsembleDirectionModel] = {}
⋮----
model = EnsembleDirectionModel(random_state=42)
⋮----
pos = int(common.get_loc(signal_idx))
⋮----
execution_idx = common[pos + 1]
⋮----
equity = cash + sum(units[s] * last_prices[s] for s in aligned)
base_weights = inverse_volatility_weights(
⋮----
signals = {}
confidences = {}
signed = base_weights.copy()
⋮----
row = features[symbol].loc[signal_idx, FEATURES]
prediction = model.predict_one(row, detect_regime(row))
side = prediction.side if prediction.confidence >= self.risk_config.min_confidence else 0
⋮----
notionals = target_notionals(equity, intelligent)
risk = evaluate_portfolio_risk(
⋮----
price = float(aligned[symbol].at[execution_idx, "Open"])
symbol_risk_config = risk_config_for_symbol(
fill = calculate_rebalance_fill(
⋮----
peak_equity = max(peak_equity, equity)
⋮----
start = test_end
⋮----
equity_curve = pd.Series(curve, dtype=float).sort_index()
```

## File: ai_trading/multiasset_checkpoint.py
```python
class MultiAssetCheckpointStore
⋮----
"""Checkpoint portfolio state and online models as one durable generation."""
⋮----
def __init__(self, root: str | Path, *, retain_generations: int = 3) -> None
⋮----
def _generation_dir(self, generation: str) -> Path
⋮----
@staticmethod
    def _validate_generation(generation: str) -> str
⋮----
@staticmethod
    def _model_filename(symbol: str) -> str
⋮----
digest = hashlib.sha256(symbol.encode("utf-8")).hexdigest()[:16]
⋮----
@staticmethod
    def _sha256(path: Path) -> str
⋮----
digest = hashlib.sha256()
⋮----
@staticmethod
    def _fsync_file(path: Path) -> None
⋮----
@staticmethod
    def _fsync_directory(path: Path) -> None
⋮----
descriptor = os.open(path, os.O_RDONLY)
⋮----
# Directory fsync is not supported on every platform/filesystem.
⋮----
@staticmethod
    def _artifact_path(directory: Path, filename: object) -> Path
⋮----
candidate = Path(filename)
⋮----
def commit(self, state: MultiAssetState, models: dict[str, object]) -> str
⋮----
generation = self._validate_generation(f"step-{state.processed_bars:012d}")
final_dir = self._generation_dir(generation)
⋮----
temp_dir = self.root / f".{generation}.{uuid.uuid4().hex}.tmp"
⋮----
state_path = temp_dir / "state.json"
⋮----
model_files: dict[str, str] = {}
⋮----
filename = self._model_filename(symbol)
model_path = temp_dir / filename
⋮----
manifest = {
manifest_path = temp_dir / "manifest.json"
⋮----
def _publish_current(self, generation: str) -> None
⋮----
pointer_tmp = self.root / f".CURRENT.{uuid.uuid4().hex}.tmp"
⋮----
def _prune_old_generations(self, *, current: str) -> None
⋮----
generations = sorted(
removable = max(0, len(generations) - (self.retain_generations - 1))
⋮----
def _prune_old_generations_best_effort(self, *, current: str) -> None
⋮----
# CURRENT is already authoritative at this point. Retention cleanup
# must not make a successfully published checkpoint look failed.
⋮----
def _load_generation(self, generation: str) -> tuple[MultiAssetState, dict[str, object]]
⋮----
directory = self._generation_dir(generation)
manifest_path = directory / "manifest.json"
manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
⋮----
state_meta = manifest["state"]
state_path = self._artifact_path(directory, state_meta["file"])
⋮----
payload = json.loads(state_path.read_text(encoding="utf-8"))
⋮----
state = MultiAssetState(**payload)
expected_generation = self._validate_generation(f"step-{state.processed_bars:012d}")
⋮----
models: dict[str, object] = {}
⋮----
path = self._artifact_path(directory, metadata["file"])
expected_filename = self._model_filename(symbol)
⋮----
def _newer_valid_generation(self, current: str | None) -> str | None
⋮----
candidates = sorted(
⋮----
def load(self) -> tuple[MultiAssetState, dict[str, object]] | None
⋮----
current: str | None = None
⋮----
current = self.current_path.read_text(encoding="utf-8").strip()
⋮----
current = self._validate_generation(current)
loaded = self._load_generation(current)
⋮----
loaded = None
⋮----
recovered = self._newer_valid_generation(current)
```

## File: ai_trading/multiasset_evolution.py
```python
@dataclass(frozen=True)
class MultiAssetEvolutionResult
⋮----
symbols: tuple[str, ...]
evolved_symbols: int
generation: int
portfolio_score: float
diversified: bool
max_pair_correlation: float
rolled_back: bool
accepted: bool
reason: str
⋮----
series: dict[str, pd.Series] = {}
⋮----
parts = record.name.split(":")
horizon_part = next(
threshold_part = next((p for p in parts if p.startswith("t")), None)
⋮----
horizon = int(horizon_part[1:])
threshold = float(threshold_part[1:])
⋮----
per_symbol: dict[str, pd.Series] = {}
⋮----
returns = _symbol_pool_returns(df, symbol=symbol, records=records)
⋮----
frame = pd.DataFrame(per_symbol).dropna()
⋮----
def _score(returns: pd.Series | None) -> float
⋮----
equity = (1.0 + returns).cumprod() * 100_000.0
⋮----
pool = pool or ExpertPoolStore()
generations = generations or GenerationStore(
⋮----
symbols = tuple(sorted(markets))
baseline_records = pool.load()
⋮----
baseline_score = _score(baseline_returns)
⋮----
baseline_active = [
⋮----
evolved = 0
local_rollback = False
⋮----
result = run_evolution_cycle(
⋮----
local_rollback = local_rollback or result.rolled_back
⋮----
candidate_records = pool.load()
⋮----
candidate_score = _score(candidate_returns)
diversity = _diversity(candidate_frame, max_pair_correlation)
⋮----
decision = evaluate_global_generation(
⋮----
rolled_back = local_rollback
⋮----
rolled_back = True
⋮----
final_records = pool.load()
⋮----
final_score = _score(final_returns)
final_diversity = _diversity(final_frame, max_pair_correlation)
final_active = [
final_snapshot = generations.snapshot(final_active, final_score)
```

## File: ai_trading/multiasset_market_context.py
```python
@dataclass(frozen=True)
class MultiAssetMarketContext
⋮----
closes: dict[str, pd.Series]
opens: dict[str, pd.Series]
features_by_symbol: dict[str, pd.DataFrame]
labels_by_symbol: dict[str, pd.Series]
execution_time: str
returns: pd.DataFrame
⋮----
closes: dict[str, pd.Series] = {}
opens: dict[str, pd.Series] = {}
execution_times: set[str] = set()
features_by_symbol: dict[str, pd.DataFrame] = {}
labels_by_symbol: dict[str, pd.Series] = {}
⋮----
required_columns = {"Open", "High", "Low", "Close", "Volume"}
⋮----
missing_columns = required_columns.difference(market.columns)
⋮----
latest_open = float(market["Open"].iloc[-1])
latest_close = float(market["Close"].iloc[-1])
⋮----
execution_time = next(iter(execution_times))
⋮----
close_frame = pd.DataFrame(closes).dropna()
returns = close_frame.pct_change().dropna()
```

## File: ai_trading/multiasset_runtime.py
```python
@dataclass(frozen=True)
class MultiAssetStepResult
⋮----
processed: bool
timestamp: str | None
equity: float
cash: float
weights: dict[str, float]
notionals: dict[str, float]
signals: dict[str, int]
confidences: dict[str, float]
risk_approved: bool
risk_reasons: tuple[str, ...]
⋮----
class MultiAssetPaperRuntime
⋮----
@staticmethod
    def _symbol_key(symbol: str) -> str
⋮----
@staticmethod
    def _legacy_symbol_key(symbol: str) -> str
⋮----
def _specialist_path(self, symbol: str, kind: str) -> Path
⋮----
def _legacy_specialist_path(self, symbol: str, kind: str) -> Path
⋮----
path = self._specialist_path(symbol, kind)
⋮----
legacy_path = self._legacy_specialist_path(symbol, kind)
⋮----
model = self._require_model_type(
⋮----
temp = path.with_suffix(".tmp")
⋮----
train_idx = features.index[features.index < signal_idx]
train_idx = train_idx.intersection(labels.dropna().index)
model = SpecialistDirectionModel(kind, random_state=42)
⋮----
def _batch_model_path(self, symbol: str) -> Path
⋮----
def _legacy_batch_model_path(self, symbol: str) -> Path
⋮----
path = self._batch_model_path(symbol)
⋮----
legacy_path = self._legacy_batch_model_path(symbol)
⋮----
model = EnsembleDirectionModel(random_state=42)
⋮----
def _model_path(self, symbol: str) -> Path
⋮----
def _legacy_model_path(self, symbol: str) -> Path
⋮----
def _load_model(self, symbol: str) -> RiverDirectionModel
⋮----
path = self._model_path(symbol)
⋮----
legacy_path = self._legacy_model_path(symbol)
⋮----
def _save_model(self, symbol: str, model: RiverDirectionModel) -> None
⋮----
def step(self, markets: dict[str, pd.DataFrame]) -> MultiAssetStepResult
⋮----
market_context = prepare_multiasset_market_context(
closes = market_context.closes
opens = market_context.opens
features_by_symbol = market_context.features_by_symbol
labels_by_symbol = market_context.labels_by_symbol
execution_time = market_context.execution_time
returns = market_context.returns
⋮----
checkpoint = self.checkpoint_store.load()
checkpoint_loaded = checkpoint is not None
⋮----
state = self.state_store.load(self.risk_config.starting_cash)
checkpoint_models: dict[str, object] = {}
⋮----
persisted_crisis = self.crisis_state_store.load()
persisted_limits = limits_for_state(persisted_crisis)
⋮----
base_weights = inverse_volatility_weights(returns, self.allocation_config)
allowed_asset_count = max(
allowed_assets = set(
allowed_assets = {
⋮----
signals: dict[str, int] = {}
confidences: dict[str, float] = {}
route_weights_by_symbol: dict[str, dict[str, float]] = {}
regimes_by_symbol: dict[str, str] = {}
calibration_by_symbol: dict[str, dict[str, dict[str, float | int]]] = {}
uncertainty_by_symbol: dict[str, dict[str, float | int]] = {}
drift_by_symbol: dict[str, dict[str, object]] = {}
opportunity_keys: list[str] = []
opportunity_alpha: dict[str, float] = {}
opportunity_quality: dict[str, float] = {}
signed_weights = base_weights.copy()
pending_online_models: dict[str, RiverDirectionModel] = {}
pending_drift_marks: list[tuple[str, int, float, float]] = []
pending_quality_updates: list[tuple[str, int, float, int]] = []
pending_meta_updates: list[tuple[MetaContext, str, bool, float]] = []
pending_lifecycle_events: list[dict[str, object]] = []
pending_economic_updates: list[tuple[str, float, float, float, float, float]] = []
⋮----
features = features_by_symbol[symbol]
labels = labels_by_symbol[symbol]
valid = features.dropna().index
⋮----
signal_idx = valid[-2]
learn_idx = valid[-3]
⋮----
clean_features = features.loc[valid, FEATURES]
drift_risk_multiplier = 1.0
retrain_triggered = False
⋮----
recent_window = clean_features.iloc[-60:]
reference_window = clean_features.iloc[:-60]
distribution_drift = detect_distribution_drift(
drift_risk_multiplier = distribution_drift.risk_multiplier
⋮----
retrain_triggered = True
⋮----
distribution_drift = None
⋮----
model = checkpoint_models.get(symbol)
⋮----
model = RiverDirectionModel()
⋮----
model = self._load_model(symbol)
⋮----
learn_label = labels.get(learn_idx)
evaluation_prediction = model.predict_one(features.loc[learn_idx, FEATURES])
⋮----
signal_row = features.loc[signal_idx, FEATURES]
river_prediction = model.predict_one(signal_row)
⋮----
regime = detect_regime(signal_row)
⋮----
batch_model = self._load_or_train_batch_model(
batch_prediction = batch_model.predict_one(signal_row, regime)
⋮----
batch_model = None
batch_prediction = None
current_equity = state.equity()
drawdown = 0.0 if state.peak_equity <= 0 else max(
drawdown_bucket = (
volatility_bucket = (
context = MetaContext(
⋮----
records = self.quality_store.load()
quality_scores = {}
model_names = ["river"] + (["ensemble"] if batch_prediction is not None else [])
⋮----
key = f"{symbol}:{model_name}"
⋮----
record = records[key]
⋮----
symbol_calibration: dict[str, dict[str, float | int]] = {}
⋮----
blend_components = [
route_candidates = {"river": river_prediction}
⋮----
base_blend = blend_predictions(blend_components)
⋮----
pool_records = self.expert_pool_store.load()
pool_budget = compute_budget_weights(pool_records)
⋮----
ranked_budget = sorted(
pool_budget = dict(ranked_budget)
⋮----
record = pool_records[expert_name]
⋮----
specialist = self._load_or_train_specialist(
⋮----
specialist_prediction = specialist.predict_one(signal_row)
candidate_name = f"specialist_{record.kind}"
⋮----
contextual_scores = self.meta_store.scores(context)
⋮----
calibration = symbol_calibration.get(calibrated_model)
⋮----
calibration_multiplier = calibration_weight_multiplier(
⋮----
kind = pool_records[expert_name].kind
⋮----
economic_stats = self.economic_meta_store.load()
⋮----
ensemble_economic_key = (
⋮----
lifecycle = evaluate_expert_lifecycle(
⋮----
economic_key = (
⋮----
economic_weight = economic_route_weight(economic_stats[economic_key])
⋮----
routed = route_predictions(
blended = routed.prediction
uncertainty = measure_expert_uncertainty(
effective_confidence = (
⋮----
opportunity_key = f"{symbol}|{model_name}|{regime.name}"
⋮----
side = blended.side
⋮----
side = 0
⋮----
realized = labels.get(learn_idx)
⋮----
realized_int = int(realized)
river_key = f"{symbol}:river"
⋮----
evaluations = [("river", evaluation_prediction)]
⋮----
batch_eval_row = features.loc[learn_idx, FEATURES]
batch_eval_prediction = batch_model.predict_one(
ensemble_key = f"{symbol}:ensemble"
⋮----
correct = evaluation.side == realized_int
edge = (
⋮----
annualized_volatility = returns.std(ddof=1) * (252 ** 0.5)
expected_alpha = pd.Series(
quality_scores = pd.Series(
alpha_weights = alpha_risk_weights(
signed_weights = signed_weights * 0.5 + alpha_weights * 0.5
⋮----
equity = state.equity()
previous_prices = {
previous_units = {
⋮----
global_allocation_report = None
pending_allocation_weights = None
⋮----
opportunity_returns = pd.DataFrame(index=returns.index)
⋮----
opportunity_symbol = key.split("|", 1)[0]
⋮----
global_allocation_report = allocate_global_capital(
⋮----
asset_scale = pd.Series(
⋮----
opportunity_symbol = str(key).split("|", 1)[0]
⋮----
intelligent_weights = intelligent_weights * asset_scale
pending_allocation_weights = global_allocation_report.weights
⋮----
# Fail closed: rejected global allocation means no target
# risk until CVaR/turnover/cost constraints are satisfied.
intelligent_weights = intelligent_weights * 0.0
⋮----
stress_report = run_stress_test(
current_drawdown = (
crisis_decision = evaluate_crisis_state(
pending_crisis_state = crisis_decision.state
intelligent_weights = (
⋮----
provisional_notionals = target_notionals(equity, intelligent_weights)
provisional_risk = evaluate_portfolio_risk(
⋮----
data_quality_reports = {
data_quality = min(
average_confidence = (
recovery_health = evaluate_recovery_health(self.lifecycle_log)
governor = evaluate_governor(
⋮----
recent_incidents = sum(
adaptive_resilience_policy = adapt_resilience_policy(
previous_resilience_state = self.resilience_state_store.load()
stability = evaluate_resilience_stability(
stability_degraded = stability.status in {"degraded", "critical"}
stability_critical = stability.status == "critical"
⋮----
effective_signals = ResilienceSignals(
resilience = evaluate_resilience(
persisted_resilience_state = ResilienceState(
pending_resilience_state = persisted_resilience_state
⋮----
intelligent_weights = intelligent_weights * resilience.exposure_cap
⋮----
previous_governor = self.governor_state_store.load()
consecutive_halts = (
pending_governor_state = GovernorState(
⋮----
intelligent_weights = intelligent_weights * governor.exposure_scale
⋮----
notionals = target_notionals(equity, intelligent_weights)
risk = evaluate_portfolio_risk(
⋮----
total_costs = 0.0
turnover_by_symbol = {symbol: 0.0 for symbol in intelligent_weights.index}
costs_by_symbol = {symbol: 0.0 for symbol in intelligent_weights.index}
⋮----
price = float(opens[symbol].iloc[-1])
position = state.positions.setdefault(symbol, AssetPosition())
symbol_risk_config = risk_config_for_symbol(
fill = calculate_rebalance_fill(
⋮----
current_prices = {
attribution = attribute_pnl(
⋮----
model_alpha_attribution = {}
⋮----
contribution = build_alpha_contribution(
⋮----
drawdown_now = (
⋮----
route_weight = route_weights_by_symbol.get(symbol, {}).get(model_name, 0.0)
```

## File: ai_trading/multiasset_scheduler.py
```python
@dataclass(frozen=True)
class MultiAssetSchedulerConfig
⋮----
poll_seconds: float = 60.0
max_iterations: int | None = None
max_consecutive_errors: int = 5
error_backoff_seconds: float = 5.0
max_error_backoff_seconds: float = 300.0
snapshot_every_iterations: int = 1
verify_audit_every_iterations: int = 1
recover_after_errors: int = 2
snapshot_retention: int = 20
⋮----
class MultiAssetPaperScheduler
⋮----
def _state_files(self) -> list
⋮----
def _jsonl_files(self) -> list
⋮----
def _active_model_files(self) -> list
⋮----
active = self.runtime.champion_registry.active()
⋮----
promotions = [
⋮----
artifact_path = promotions[-1].artifact_path
⋮----
def _snapshot_files(self) -> list
⋮----
def _audit_error(self, exc: Exception, consecutive_errors: int) -> None
⋮----
def _verify_audit(self) -> None
⋮----
report = verify_jsonl_audit(self.runtime.audit.path)
⋮----
chain = verify_audit_chain(self.runtime.audit.path)
⋮----
def _snapshot(self) -> None
⋮----
snapshot = self.snapshot_store.create(self._snapshot_files())
fingerprint = compute_session_fingerprint(
⋮----
def run(self) -> list[MultiAssetStepResult]
⋮----
startup = run_startup_check(
⋮----
recovery = recover_latest_consistent_state(
⋮----
results: list[MultiAssetStepResult] = []
iteration = 0
consecutive_errors = 0
⋮----
status = read_control_plane(
⋮----
started = monotonic()
⋮----
markets = self.data_loader()
result = self.runtime.step(markets)
⋮----
delay = min(
⋮----
elapsed = monotonic() - started
```

## File: ai_trading/multiasset_state.py
```python
@dataclass
class AssetPosition
⋮----
units: float = 0.0
last_price: float = 0.0
⋮----
@dataclass
class MultiAssetState
⋮----
cash: float
peak_equity: float
day_start_equity: float
positions: dict[str, AssetPosition] = field(default_factory=dict)
last_processed: str | None = None
processed_bars: int = 0
⋮----
def equity(self) -> float
⋮----
class MultiAssetStateStore
⋮----
def __init__(self, path: str | Path = "artifacts/multiasset_state.json") -> None
⋮----
def load(self, starting_cash: float) -> MultiAssetState
⋮----
payload = json.loads(self.path.read_text(encoding="utf-8"))
⋮----
def save(self, state: MultiAssetState) -> None
⋮----
temp = self.path.with_suffix(".tmp")
```

## File: ai_trading/online.py
```python
@dataclass
class OnlineLearningStats
⋮----
observations: int = 0
correct: int = 0
⋮----
@property
    def accuracy(self) -> float
⋮----
class RiverDirectionModel
⋮----
"""True incremental classifier updated one labeled observation at a time."""
⋮----
def __init__(self) -> None
⋮----
@staticmethod
    def _x(row: pd.Series) -> dict[str, float]
⋮----
def learn_one(self, row: pd.Series, label: int) -> None
⋮----
x = self._x(row)
before = self.predict_one(row)
⋮----
def predict_one(self, row: pd.Series) -> Prediction
⋮----
raw = self.model.predict_proba_one(x)
probabilities = {cls: float(raw.get(cls, 0.0)) for cls in self._classes}
total = sum(probabilities.values())
⋮----
probabilities = {-1: 0.0, 0: 1.0, 1: 0.0}
⋮----
probabilities = {k: v / total for k, v in probabilities.items()}
⋮----
side = max(probabilities, key=probabilities.get)
⋮----
class RiverMulticlassDirectionModel(RiverDirectionModel)
⋮----
"""Research-only three-class River alternative; not loaded by paper v1."""
```

## File: ai_trading/operational_overview.py
```python
_MTF_MIN_DIRECTIONAL_OBSERVATIONS = 100
⋮----
def _empty_model_snapshot() -> dict[str, object]
⋮----
def _empty_shadow_quality_snapshot() -> dict[str, object]
⋮----
policy = ShadowPromotionPolicy()
⋮----
policy = ShadowPromotionPolicy(min_observations=500)
⋮----
reasons = ["no benchmark-validated MTF configuration for this market"]
status = "unvalidated"
candidate_config = None
horizon_minutes = None
label = None
⋮----
reasons = [
status = "collecting"
candidate_config = config.as_dict()
horizon_minutes = config.horizon_minutes
label = {
⋮----
def _shadow_quality_snapshot(comparison) -> dict[str, object]
⋮----
observations = int(comparison.observations)
available = observations >= 5
⋮----
def quality_payload(quality) -> dict[str, object]
⋮----
gate = evaluate_shadow_promotion_gate(comparison, policy)
⋮----
def _river_v2_forward_snapshot(comparison=None) -> dict[str, object]
⋮----
"""Presentation of *observed* forward labels; never a promotion signal."""
count = int(comparison.observations) if comparison is not None else 0
⋮----
# Directional classification is not proof of net-of-cost trading edge.
⋮----
directional_observations = int(comparison.directional_observations)
directional_rate = float(comparison.directional_rate)
gate_reasons = list(gate.reasons)
⋮----
eligible_for_review = gate.eligible_for_review and not gate_reasons
⋮----
def runtime_is_consistent(persisted: PersistedRuntime) -> bool
⋮----
state = persisted.state
⋮----
def _burnin_snapshot(snapshots: tuple[BurnInSnapshot, ...]) -> dict[str, object]
⋮----
latest_bars = snapshots[-1].processed_bars if snapshots else 0
⋮----
metrics = calculate_burnin_metrics(snapshots)
⋮----
def _empty_readiness_snapshot() -> dict[str, object]
⋮----
probability = bootstrap_positive_probability(
⋮----
report = evaluate_readiness(
⋮----
runtime_parts = runtime_key.split(":", 2)
runtime_symbol = runtime_parts[1] if len(runtime_parts) > 1 else ""
mtf_config = validated_mtf_shadow_config(runtime_symbol)
⋮----
persisted = persistence.load_runtime(runtime_key, starting_cash)
status = persistence.load_runtime_status(runtime_key)
burnin_loader = getattr(persistence, "list_burnin_snapshots", None)
snapshots = (
regime_loader = getattr(persistence, "list_regimes", None)
regimes = tuple(regime_loader(runtime_key)) if callable(regime_loader) else ()
burnin = _burnin_snapshot(snapshots)
readiness = _readiness_snapshot(snapshots, regimes, status)
except Exception:  # noqa: BLE001 - observability boundary must sanitize backend failures
⋮----
performance = empty_performance_payload()
performance_loader = getattr(persistence, "load_trade_performance", None)
⋮----
performance = performance_payload(performance_loader(runtime_key))
except Exception:  # noqa: BLE001 - optional observability must not break runtime status
⋮----
shadow_quality = _empty_shadow_quality_snapshot()
shadow_loader = getattr(persistence, "load_shadow_quality", None)
⋮----
shadow_quality = _shadow_quality_snapshot(shadow_loader(runtime_key))
⋮----
river_v2_quality = _river_v2_forward_snapshot()
river_v2_loader = getattr(persistence, "load_river_v2_forward_quality", None)
⋮----
river_v2_quality = _river_v2_forward_snapshot(river_v2_loader(runtime_key))
except Exception:  # noqa: BLE001 - read-only research cannot break the dashboard
⋮----
mtf_shadow_quality = _empty_mtf_shadow_quality_snapshot(mtf_config)
mtf_shadow_loader = getattr(persistence, "load_mtf_shadow_quality", None)
⋮----
mtf_shadow_quality = _mtf_shadow_quality_snapshot(
except Exception:  # noqa: BLE001 - optional observer must not break status
⋮----
status_snapshot = runtime_status_snapshot(status)
engine_status = str(status_snapshot["engine_status"])
lag_detected = engine_status == "STALE"
consecutive_cycle_errors = (
⋮----
model = persisted.model
⋮----
alerts: list[str] = []
⋮----
model_snapshot: dict[str, object]
⋮----
model_snapshot = _empty_model_snapshot()
⋮----
model_snapshot = {
```

## File: ai_trading/orchestrator.py
```python
@dataclass(frozen=True)
class OrchestrationResult
⋮----
runtime: RuntimeStepResult
health: HealthDecision | None
regime_validation: RegimeValidation | None
learning_cycle: ContinuousCycleResult | None
learning_cycle_triggered: bool
trigger_reason: str | None
⋮----
class AutonomousPaperOrchestrator
⋮----
report = WalkForwardBacktester(
⋮----
features = make_features(df).dropna()
feature_split = max(60, int(len(features) * 0.75))
strategy_returns = report.equity_curve.pct_change().dropna()
return_split = max(20, int(len(strategy_returns) * 0.75))
⋮----
drift = detect_drift(
⋮----
runtime_result = self.runtime.step(df)
⋮----
health: HealthDecision | None = None
regime_validation: RegimeValidation | None = None
current_metrics: PerformanceMetrics | None = None
⋮----
trigger_reason: str | None = None
⋮----
trigger_reason = "scheduled learning interval reached"
⋮----
trigger_reason = f"health degradation: {health.reason}"
⋮----
trigger_reason = f"regime validation failed: {regime_validation.reason}"
⋮----
governor_state = self.governor_state_store.load()
⋮----
trigger_reason = (
⋮----
cycle: ContinuousCycleResult | None = None
⋮----
active = self.registry.active()
⋮----
champion_metrics = PerformanceMetrics(**active.metrics)
⋮----
champion_metrics = current_metrics
⋮----
champion_metrics = self._health_checks(df)[2]
⋮----
cycle = run_learning_cycle(
⋮----
state = self.runtime.state_store.load(self.runtime.risk_config.starting_cash)
```

## File: ai_trading/paper_cycle_service.py
```python
@dataclass(frozen=True)
class ProductionPaperCycleSettings
⋮----
symbol: str = "GC=F"
period: str = "5d"
interval: str = "5m"
max_catchup_bars: int = DEFAULT_MAX_CATCHUP_BARS
poll_seconds: float = 300.0
shadow_challenger_enabled: bool = False
mtf_period: str = "1mo"
⋮----
class PaperCycleServiceError(RuntimeError)
⋮----
def __init__(self, *, code: str, error_type: str) -> None
⋮----
def _now_utc() -> str
⋮----
def _default_runner_factory(persistence: PaperPersistence) -> PaperCycleRunner
⋮----
_SAFE_RUNTIME_FAILURES = {
⋮----
def _safe_failure_detail(exc: Exception) -> str
⋮----
message = str(exc)
code = _SAFE_RUNTIME_FAILURES.get(message)
⋮----
"""Reuse a completed decision only when the durable runtime has not advanced.

    The dashboard independently checks session state, heartbeat and bar age
    before exposing this decision; a past decision never becomes a new trade.
    """
⋮----
runtime_key = build_runtime_key(settings.symbol, settings.interval)
starting_cash = RiskConfig().starting_cash
cycle_started = perf_counter()
⋮----
backend = persistence
⋮----
backend = persistence_factory()
except Exception as exc:  # noqa: BLE001 - sanitize provider errors here
⋮----
previous_status = backend.load_runtime_status(runtime_key)
previous_cycle_errors = (
⋮----
except Exception as exc:  # noqa: BLE001 - storage boundary is fail-closed
⋮----
runner = runner_factory(backend)
⋮----
result = runner.run_once(
⋮----
state = backend.load_runtime(runtime_key, starting_cash).state
equity = state.cash + state.units * state.last_price
cycle_duration_seconds = perf_counter() - cycle_started
reuse_decision = _can_reuse_last_paper_decision(
last_decision = previous_status if reuse_decision else None
⋮----
# A no-op poll must not erase a still-current paper decision.
# "reason" still describes this poll; time/approval stay unchanged.
⋮----
except Exception as exc:  # noqa: BLE001 - sanitize execution/provider failures
⋮----
except Exception:  # noqa: BLE001, S110 - best-effort failure reporting
```

## File: ai_trading/paper_cycle.py
```python
DEFAULT_MAX_CATCHUP_BARS = 72
_MAX_PROVIDER_GAP_RESUME = pd.Timedelta(days=3)
_FIVE_MINUTES = pd.Timedelta(minutes=5)
_CANDLE_FINALITY_BUFFER = pd.Timedelta(seconds=2)
⋮----
def _utc_now() -> pd.Timestamp
⋮----
"""Exclude provider candles that have not finished before paper execution.

    Yahoo's intraday response can contain an OHLC row whose timestamp is the
    *start* of the currently forming candle. Executing its partial close would
    permanently persist a decision against a price that later changes.
    Date-only and historical non-5m pipelines keep their prior behaviour.
    Naive timestamps are interpreted as UTC, as in the existing paper runner.
    """
⋮----
current = _utc_now() if now is None else pd.Timestamp(now)
⋮----
current = current.tz_convert("UTC")
timestamps = (
completed = timestamps + _FIVE_MINUTES + _CANDLE_FINALITY_BUFFER <= current
⋮----
def _utc_timestamp(value: object) -> pd.Timestamp
⋮----
timestamp = pd.Timestamp(value)
⋮----
timestamp = pd.Timestamp(execution_idx)
epoch_minutes = timestamp.value // (60 * 1_000_000_000)
⋮----
@dataclass(frozen=True)
class PaperCycleResult
⋮----
processed: int
remaining_backlog: bool
last_processed: str | None
processed_bars: int
reason: str
mtf_evaluated: bool = False
partial_failure: bool = False
failed_markets: int = 0
side: int = 0
confidence: float = 0.0
approved: bool = False
decision_reason: str | None = None
⋮----
class PaperCycleRunner
⋮----
"""Run a bounded one-shot paper cycle against durable runtime state."""
⋮----
@staticmethod
    def _is_logically_fresh(snapshot: PersistedRuntime) -> bool
⋮----
state = snapshot.state
⋮----
last_processed = snapshot.state.last_processed
⋮----
positions = {str(value): index for index, value in enumerate(eligible)}
position = positions.get(last_processed)
⋮----
market_positions = {
market_position = market_positions.get(last_processed)
⋮----
persisted_time = _utc_timestamp(last_processed)
raw_times = tuple(_utc_timestamp(value) for value in market_index)
eligible_times = tuple(_utc_timestamp(value) for value in eligible)
⋮----
first_raw = raw_times[0]
last_raw = raw_times[-1]
⋮----
runtime_key = build_runtime_key(symbol, interval)
runtime = self.runtime_factory(
market = _completed_market_bars(
quality = evaluate_market_data_quality(market)
⋮----
reasons = ",".join(quality.reasons) or "score below threshold"
⋮----
prepared = runtime.prepare_market(market)
eligible = prepared.eligible
⋮----
snapshot = self.persistence.load_runtime(
pending = self._pending_targets(snapshot, eligible, market.index)
⋮----
shadow_result = None
shadow_target: str | None = None
mtf_shadow_result = None
mtf_attach_target: str | None = None
⋮----
shadow_target = str(pending[0])
shadow_result = evaluate_shadow_challenger(
except Exception:  # noqa: BLE001 - observer must never disrupt execution
⋮----
shadow_target = None
⋮----
mtf_config = validated_mtf_shadow_config(symbol)
mtf_candidate = (
⋮----
mtf_market = (
mtf_quality = evaluate_market_data_quality(mtf_market)
⋮----
mtf_current = {
⋮----
mtf_execution = select_observable_execution_target(
⋮----
mtf_shadow_result = evaluate_multi_timeframe_shadow(
⋮----
mtf_attach_target = str(mtf_candidate)
⋮----
mtf_attach_target = None
⋮----
processed = 0
attempts = 0
last_decision = None
⋮----
target = pending[0]
observer_kwargs = {}
⋮----
river_v2 = observe_river_v2_forward(
⋮----
except Exception:  # noqa: BLE001 - research observer cannot stop paper trades
⋮----
result = runtime.step_prepared(
⋮----
last_decision = result
⋮----
remaining_backlog = bool(pending)
⋮----
reason = "catch-up pending"
⋮----
reason = f"processed {processed} bar(s)"
⋮----
reason = "concurrent progress observed"
```

## File: ai_trading/paper_execution.py
```python
@dataclass(frozen=True)
class RebalanceFill
⋮----
desired_units: float
delta_units: float
gross_turnover: float
costs: float
realized_gross_pnl: float | None
realized_net_pnl: float | None
next_average_entry_price: float
⋮----
values = {
⋮----
desired_units = values["target_notional"] / values["price"]
delta_units = desired_units - values["current_units"]
gross_turnover = abs(delta_units) * values["price"]
costs = gross_turnover * (
⋮----
current = values["current_units"]
average = values["current_average_entry_price"]
epsilon = 1e-12
closing_units = 0.0
⋮----
closing_units = min(abs(delta_units), abs(current))
⋮----
direction = 1.0 if current > 0 else -1.0
realized_gross_pnl: float | None = (
⋮----
realized_gross_pnl = None
⋮----
realized_gross_pnl = 0.0
⋮----
next_average_entry_price = 0.0
⋮----
next_average_entry_price = values["price"]
⋮----
added_units = abs(desired_units) - abs(current)
next_average_entry_price = (
⋮----
next_average_entry_price = average
⋮----
realized_net_pnl = (
```

## File: ai_trading/paper_readiness_evidence.py
```python
@lru_cache(maxsize=16)
def bootstrap_positive_probability(equities: tuple[float, ...]) -> float | None
⋮----
report = bootstrap_equity_curve(pd.Series(equities, dtype=float))
```

## File: ai_trading/parameter_sensitivity.py
```python
@dataclass(frozen=True)
class SensitivityScenario
⋮----
name: str
confidence_multiplier: float = 1.0
threshold_multiplier: float = 1.0
position_multiplier: float = 1.0
⋮----
@dataclass(frozen=True)
class SensitivityResult
⋮----
scenario: SensitivityScenario
total_return: float
excess_return: float
sharpe: float
max_drawdown: float
trades: int
⋮----
DEFAULT_SENSITIVITY_SCENARIOS = (
⋮----
results: list[SensitivityResult] = []
⋮----
risk = replace(
model = replace(
report = WalkForwardBacktester(
⋮----
def _bounded(value: float, lower: float, upper: float) -> float
```

## File: ai_trading/performance_metrics.py
```python
@dataclass(frozen=True)
class TradePerformanceMetrics
⋮----
trade_count: int
pnl_observations: int
realized_pnl: float
average_pnl: float
gross_profit: float
gross_loss: float
profit_factor: float | None
max_drawdown: float
⋮----
observations = trade_count if pnl_observations is None else pnl_observations
⋮----
average_pnl = realized_pnl / observations if observations else 0.0
⋮----
profit_factor = None
⋮----
profit_factor = gross_profit / gross_loss
⋮----
profit_factor = float("inf")
⋮----
snapshots = tuple(trades)
pnls = tuple(trade.pnl for trade in snapshots if trade.pnl_known is True)
realized_pnl = sum(pnls)
gross_profit = sum(pnl for pnl in pnls if pnl > 0.0)
gross_loss = -sum(pnl for pnl in pnls if pnl < 0.0)
⋮----
cumulative_pnl = 0.0
peak_pnl = 0.0
max_drawdown = 0.0
⋮----
peak_pnl = max(peak_pnl, cumulative_pnl)
max_drawdown = max(max_drawdown, peak_pnl - cumulative_pnl)
⋮----
"""Match normalized paper sleeves to the weights used in portfolio equity."""
⋮----
"""Compute cash PnL and drawdown at actual sleeve allocations.

    Trade count and PnL coverage remain event counts, not fractional weights.
    """
⋮----
def empty_performance_payload() -> dict[str, object]
⋮----
def performance_payload(metrics: TradePerformanceMetrics) -> dict[str, object]
⋮----
trade_count = int(metrics.trade_count)
observations = int(metrics.pnl_observations)
available = observations > 0
profit_factor = metrics.profit_factor
profit_factor_infinite = (
```

## File: ai_trading/performance.py
```python
@dataclass(frozen=True)
class PerformanceMetrics
⋮----
total_return: float
annualized_return: float
annualized_volatility: float
sharpe: float
sortino: float
max_drawdown: float
calmar: float
⋮----
def as_dict(self) -> dict[str, float]
⋮----
def _safe_ratio(numerator: float, denominator: float) -> float
⋮----
def infer_periods_per_year(index: pd.Index) -> float
⋮----
timestamps = pd.to_datetime(index, utc=True, errors="coerce")
timestamps = timestamps[~timestamps.isna()]
⋮----
elapsed_seconds = float((timestamps[-1] - timestamps[0]).total_seconds())
⋮----
elapsed_years = elapsed_seconds / (365.25 * 24 * 60 * 60)
⋮----
def _annualized_return(start: float, end: float, years: float) -> float
⋮----
log_growth = float(np.log(end / start) / years)
max_log = float(np.log(np.finfo(float).max))
min_log = float(np.log(np.finfo(float).tiny))
⋮----
def compute_metrics(equity: pd.Series, periods_per_year: float = 252.0) -> PerformanceMetrics
⋮----
clean = equity.astype(float).dropna()
⋮----
returns = clean.pct_change().dropna()
total_return = float(clean.iloc[-1] / clean.iloc[0] - 1.0)
⋮----
years = max((len(returns) / periods_per_year), 1.0 / periods_per_year)
annualized_return = _annualized_return(
⋮----
volatility = float(returns.std(ddof=1) * np.sqrt(periods_per_year)) if len(returns) > 1 else 0.0
mean_ann = float(returns.mean() * periods_per_year) if len(returns) else 0.0
sharpe = _safe_ratio(mean_ann, volatility)
⋮----
downside = returns[returns < 0]
downside_dev = (
sortino = _safe_ratio(mean_ann, downside_dev)
⋮----
running_max = clean.cummax()
drawdowns = 1.0 - clean / running_max
max_drawdown = float(drawdowns.max())
calmar = _safe_ratio(annualized_return, max_drawdown)
⋮----
clean = prices.astype(float).dropna()
```

## File: ai_trading/persistence_factory.py
```python
database_url = os.getenv("AI_TRADING_DATABASE_URL", "").strip()
⋮----
persistence = PostgresPaperPersistence(database_url, pooled=pool_connections)
```

## File: ai_trading/persistence.py
```python
class CommitOutcome(str, Enum)
⋮----
COMMITTED = "committed"
CONFLICT = "conflict"
⋮----
@dataclass(frozen=True)
class ModelBlob
⋮----
format: str
version: int
payload: bytes
sha256: str
⋮----
@dataclass(frozen=True)
class PersistedRuntime
⋮----
state: RuntimeState
model: ModelBlob | None
revision: int
is_new: bool
⋮----
@dataclass(frozen=True)
class SchedulerDelivery
⋮----
timestamp_utc: str
source: str
status_code: int
ok: bool
processed: int | None = None
⋮----
@dataclass(frozen=True)
class RuntimeStepCommit
⋮----
expected_revision: int
⋮----
model: ModelBlob
trade: TradeSnapshot | None
audit_event: str
audit_payload: dict[str, Any]
observed_regime: str | None = None
⋮----
class PaperPersistence(Protocol)
⋮----
def initialize_schema(self) -> None: ...
⋮----
def load_runtime(self, runtime_key: str, starting_cash: float) -> PersistedRuntime: ...
⋮----
def commit_step(self, runtime_key: str, commit: RuntimeStepCommit) -> CommitOutcome: ...
⋮----
def load_trade_performance(self, runtime_key: str) -> TradePerformanceMetrics: ...
⋮----
def list_burnin_snapshots(self, runtime_key: str) -> tuple[BurnInSnapshot, ...]: ...
⋮----
def list_regimes(self, runtime_key: str) -> tuple[str, ...]: ...
⋮----
def save_runtime_status(self, runtime_key: str, status: HostedRuntimeStatus) -> None: ...
⋮----
def load_runtime_status(self, runtime_key: str) -> HostedRuntimeStatus | None: ...
⋮----
def record_scheduler_delivery(self, delivery: SchedulerDelivery) -> None: ...
⋮----
def build_runtime_key(symbol: str, interval: str) -> str
⋮----
@dataclass(frozen=True)
class ModelArtifact
⋮----
path: Path
metadata: dict[str, Any]
⋮----
class ModelStore
⋮----
def __init__(self, root: str | Path = "artifacts/models") -> None
⋮----
def save(self, name: str, model: object, metadata: dict[str, Any] | None = None) -> ModelArtifact
⋮----
path = self.root / f"{name}.joblib"
payload = {"model": model, "metadata": metadata or {}}
⋮----
def load(self, name: str) -> ModelArtifact
⋮----
payload = joblib.load(path)
⋮----
def load_model(self, name: str) -> object
⋮----
def activate(self, name: str) -> ModelArtifact
⋮----
artifact = self.load(name)
⋮----
temp = self.pointer_path.with_suffix(".tmp")
⋮----
def active_name(self) -> str | None
⋮----
payload = json.loads(self.pointer_path.read_text(encoding="utf-8"))
value = payload.get("active")
⋮----
def load_active_model(self) -> object
⋮----
name = self.active_name()
```

## File: ai_trading/pnl_attribution.py
```python
@dataclass(frozen=True)
class AssetPnL
⋮----
symbol: str
pnl: float
return_contribution: float
⋮----
out: dict[str, AssetPnL] = {}
⋮----
pnl = float(qty) * (float(current_prices[symbol]) - float(previous_prices[symbol]))
⋮----
def attribution_frame(attribution: dict[str, AssetPnL]) -> pd.DataFrame
```

## File: ai_trading/portfolio_intelligence.py
```python
@dataclass(frozen=True)
class PortfolioIntelligenceConfig
⋮----
target_annual_volatility: float = 0.12
min_leverage: float = 0.10
max_leverage: float = 1.00
drawdown_soft_limit: float = 0.05
drawdown_hard_limit: float = 0.12
stress_vol_multiplier: float = 1.75
confidence_floor: float = 0.50
confidence_power: float = 2.0
correlation_soft_limit: float = 0.70
correlation_hard_limit: float = 0.90
⋮----
def __post_init__(self) -> None
⋮----
@dataclass(frozen=True)
class PortfolioIntelligenceReport
⋮----
leverage: float
estimated_annual_volatility: float
drawdown_scale: float
stress_scale: float
confidence_scale: float
correlation_scale: float
max_pair_correlation: float
stress_detected: bool
⋮----
aligned = returns.reindex(columns=weights.index).dropna()
⋮----
cov = aligned.cov().to_numpy(dtype=float) * periods_per_year
w = weights.to_numpy(dtype=float)
⋮----
variance = float(w.T @ cov @ w)
⋮----
active_assets = [asset for asset in weights.index if abs(float(weights.loc[asset])) > 1e-12]
⋮----
aligned = returns.reindex(columns=active_assets).dropna()
⋮----
corr = aligned.corr().abs()
max_corr = 0.0
⋮----
value = corr.at[asset, other]
⋮----
max_corr = max(max_corr, float(value))
⋮----
span = config.correlation_hard_limit - config.correlation_soft_limit
⋮----
progress = (max_pair_correlation - config.correlation_soft_limit) / span
⋮----
drawdown = max(0.0, 1.0 - current_equity / peak_equity)
⋮----
span = config.drawdown_hard_limit - config.drawdown_soft_limit
progress = (drawdown - config.drawdown_soft_limit) / span
⋮----
config = config or PortfolioIntelligenceConfig()
weights = base_weights.astype(float).copy()
⋮----
confidence_multipliers = pd.Series(0.0, index=weights.index, dtype=float)
⋮----
confidence = float(confidences.get(asset, 0.0))
⋮----
confidence = 0.0
confidence = min(1.0, max(0.0, confidence))
⋮----
normalized = (confidence - config.confidence_floor) / (1.0 - config.confidence_floor)
⋮----
gross = float(weights.abs().sum())
⋮----
estimated_vol = estimate_portfolio_volatility(weights, returns)
⋮----
vol_scale = config.min_leverage
⋮----
vol_scale = config.target_annual_volatility / estimated_vol
⋮----
aligned_returns = returns.reindex(columns=weights.index)
recent_vol = aligned_returns.tail(20).std(ddof=1).mean()
baseline_vol = aligned_returns.tail(120).std(ddof=1).mean()
stress_detected = bool(
stress_scale = 0.5 if stress_detected else 1.0
drawdown_scale = _drawdown_scale(current_equity, peak_equity, config)
max_pair_correlation = _active_max_pair_correlation(weights, returns)
correlation_scale = _correlation_scale(max_pair_correlation, config)
⋮----
confidence_scale = float(confidence_multipliers.mean()) if len(confidence_multipliers) else 0.0
base_leverage = min(
leverage = max(
⋮----
intelligent_weights = weights * leverage
```

## File: ai_trading/portfolio_risk.py
```python
@dataclass(frozen=True)
class PortfolioRiskConfig
⋮----
max_gross_exposure: float = 1.00
max_net_exposure: float = 0.75
max_asset_exposure: float = 0.35
max_pair_correlation: float = 0.90
⋮----
def __post_init__(self) -> None
⋮----
@dataclass(frozen=True)
class PortfolioRiskReport
⋮----
approved: bool
gross_exposure: float
net_exposure: float
max_asset_exposure: float
max_pair_correlation: float
reasons: tuple[str, ...]
⋮----
config = config or PortfolioRiskConfig()
⋮----
exposures = notionals.astype(float) / equity
gross = float(exposures.abs().sum())
net = float(abs(exposures.sum()))
max_asset = float(exposures.abs().max()) if len(exposures) else 0.0
⋮----
corr = returns.astype(float).corr().abs()
max_corr = 0.0
⋮----
value = corr.at[a, b]
⋮----
max_corr = max(max_corr, float(value))
⋮----
reasons: list[str] = []
```

## File: ai_trading/portfolio_selection.py
```python
@dataclass(frozen=True)
class ReplacementDecision
⋮----
replace: bool
reason: str
```

## File: ai_trading/portfolio.py
```python
@dataclass(frozen=True)
class AllocationConfig
⋮----
max_asset_weight: float = 0.35
min_asset_weight: float = 0.0
target_gross_exposure: float = 1.0
correlation_penalty: float = 0.50
⋮----
def __post_init__(self) -> None
⋮----
base = weights.clip(lower=0.0).astype(float)
⋮----
result = pd.Series(0.0, index=base.index, dtype=float)
free = list(base.index)
remaining = float(target_sum)
⋮----
free_base = base.loc[free]
total = float(free_base.sum())
⋮----
proposal = pd.Series(remaining / len(free), index=free, dtype=float)
⋮----
proposal = free_base / total * remaining
⋮----
over = proposal[proposal > max_weight + 1e-12]
⋮----
config = config or AllocationConfig()
clean = returns.astype(float).dropna(how="all")
⋮----
vol = clean.std(ddof=1).replace(0.0, np.nan)
inv = (1.0 / vol).replace([np.inf, -np.inf], np.nan).fillna(0.0)
⋮----
raw = pd.Series(1.0 / len(inv), index=inv.index, dtype=float)
⋮----
raw = inv / inv.sum()
⋮----
corr = clean.corr().fillna(0.0).abs()
penalties = pd.Series(1.0, index=raw.index, dtype=float)
⋮----
peers = corr.loc[asset].drop(labels=[asset], errors="ignore")
avg_corr = float(peers.mean()) if len(peers) else 0.0
⋮----
adjusted = raw * penalties
⋮----
adjusted = raw.copy()
⋮----
adjusted = adjusted.clip(lower=config.min_asset_weight)
⋮----
clean = returns.astype(float).dropna()
⋮----
cov = clean.cov().to_numpy(dtype=float)
n = cov.shape[0]
weights = np.full(n, 1.0 / n, dtype=float)
target_rc = np.full(n, 1.0 / n, dtype=float)
⋮----
portfolio_var = float(weights @ cov @ weights)
⋮----
marginal = cov @ weights
risk_contrib = weights * marginal
total_rc = float(risk_contrib.sum())
⋮----
normalized_rc = risk_contrib / total_rc
error = normalized_rc - target_rc
⋮----
safe_rc = np.where(np.abs(normalized_rc) < 1e-12, 1e-12, normalized_rc)
⋮----
weights = np.clip(weights, 1e-12, None)
⋮----
raw = pd.Series(weights, index=clean.columns, dtype=float)
```

## File: ai_trading/postgres_persistence.py
```python
_SCHEMA_STATEMENTS = (
⋮----
def _trade_event_key(trade: TradeSnapshot) -> str
⋮----
payload = asdict(trade)
⋮----
canonical = json.dumps(
⋮----
class PostgresPaperPersistence(PaperPersistence)
⋮----
# Reuse up to four connections for bursty dashboard reads. With min_size=0,
# close idle connections promptly so serverless Postgres can scale to zero
# between 15-minute paper cycles instead of staying awake for 10 minutes.
# CLI jobs remain one-shot by default.
⋮----
def _connect(self)
⋮----
def close(self) -> None
⋮----
def initialize_schema(self) -> None
⋮----
def load_runtime(self, runtime_key: str, starting_cash: float) -> PersistedRuntime
⋮----
is_new = cursor.fetchone() is not None
⋮----
row = cursor.fetchone()
⋮----
model_row = cursor.fetchone()
⋮----
state = RuntimeState(
model = None
⋮----
model = ModelBlob(
⋮----
def commit_step(self, runtime_key: str, commit: RuntimeStepCommit) -> CommitOutcome
⋮----
current = cursor.fetchone()
⋮----
trade = commit.trade
⋮----
trade_inserted = cursor.fetchone() is not None
⋮----
pnl_known = bool(trade.pnl_known)
pnl = float(trade.pnl) if pnl_known else 0.0
pnl_observations = 1 if pnl_known else 0
⋮----
previous = cursor.fetchone()
previous_hash = "GENESIS" if previous is None else str(previous["hash"])
audit = build_audit_record(
⋮----
state = commit.state
⋮----
where = "WHERE runtime_key = %s" if runtime_key is not None else ""
params: list[object] = [] if runtime_key is None else [runtime_key]
order = "ORDER BY id ASC"
⋮----
order = "ORDER BY id DESC LIMIT %s"
⋮----
query = f"""
⋮----
rows = cursor.fetchall()
⋮----
def load_trade_performance(self, runtime_key: str) -> TradePerformanceMetrics
⋮----
weights = resolved_portfolio_allocations(runtime_keys, allocations)
⋮----
def list_burnin_snapshots(self, runtime_key: str) -> tuple[BurnInSnapshot, ...]
⋮----
def list_regimes(self, runtime_key: str) -> tuple[str, ...]
⋮----
def load_shadow_quality(self, runtime_key: str) -> ShadowQualityComparison
⋮----
payloads = []
⋮----
payload = row["payload"]
⋮----
payload = json.loads(payload)
⋮----
def load_river_v2_forward_quality(self, runtime_key: str) -> RiverV2ForwardComparison
⋮----
"""Bounded, read-only audit replay for one-bar v1/v2 forward comparison."""
⋮----
def save_runtime_status(self, runtime_key: str, status: HostedRuntimeStatus) -> None
⋮----
payload = asdict(status)
⋮----
def load_runtime_status(self, runtime_key: str) -> HostedRuntimeStatus | None
⋮----
def record_scheduler_delivery(self, delivery: SchedulerDelivery) -> None
```

## File: ai_trading/process_watch.py
```python
@dataclass(frozen=True)
class ProcessWatchResult
⋮----
exit_code: int | None
timed_out: bool
runtime_seconds: float
⋮----
started = time.monotonic()
⋮----
exit_code = process.wait()
⋮----
exit_code = process.wait(timeout=timeout_seconds)
```

## File: ai_trading/promotion_guard.py
```python
@dataclass(frozen=True)
class PromotionPolicy
⋮----
min_score_improvement: float = 0.0
min_sharpe_delta: float = -0.05
min_sortino_delta: float = -0.05
max_drawdown_increase: float = 0.02
min_calmar_delta: float = -0.05
required_metrics: tuple[str, ...] = (
⋮----
@dataclass(frozen=True)
class PromotionDecision
⋮----
approved: bool
reasons: tuple[str, ...]
score_delta: float
metric_deltas: dict[str, float]
⋮----
policy = policy or PromotionPolicy()
reasons: list[str] = []
⋮----
values = [champion_score, challenger_score]
⋮----
missing = [
⋮----
score_delta = float(challenger_score - champion_score)
metric_deltas = {
```

## File: ai_trading/promotion.py
```python
@dataclass(frozen=True)
class PromotionPolicy
⋮----
min_sharpe_improvement: float = 0.10
min_return_improvement: float = 0.00
max_drawdown_increase: float = 0.02
min_period_win_rate: float = 0.60
⋮----
@dataclass(frozen=True)
class PromotionDecision
⋮----
promote: bool
reason: str
⋮----
policy = policy or PromotionPolicy()
⋮----
sharpe_gain = challenger.sharpe - champion.sharpe
return_gain = challenger.total_return - champion.total_return
drawdown_increase = challenger.max_drawdown - champion.max_drawdown
⋮----
wins = 0
⋮----
decision = evaluate_challenger(champion, challenger, policy)
⋮----
win_rate = wins / len(champion_periods)
```

## File: ai_trading/purged_cv.py
```python
@dataclass(frozen=True)
class PurgedFold
⋮----
train_index: pd.Index
test_index: pd.Index
⋮----
required = (
⋮----
result: list[PurgedFold] = []
cursor = min_train_bars
⋮----
train_end = max(0, cursor - purge_bars)
test_start = cursor
test_end = test_start + test_bars
⋮----
train_index = index[:train_end]
test_index = index[test_start:test_end]
⋮----
cursor = test_end + embargo_bars
```

## File: ai_trading/qualification_guard.py
```python
@dataclass(frozen=True)
class QualificationGuardResult
⋮----
allowed: bool
reasons: tuple[str, ...]
⋮----
reasons: list[str] = []
⋮----
created = datetime.fromisoformat(record.created_at_utc)
⋮----
created = created.replace(tzinfo=UTC)
age_hours = (datetime.now(UTC) - created).total_seconds() / 3600.0
⋮----
effective_reliability = reliability
⋮----
effective_reliability = ReliabilityReport(
```

## File: ai_trading/qualification_store.py
```python
@dataclass(frozen=True)
class QualificationRecord
⋮----
created_at_utc: str
passed: bool
success_ratio: float
reasons: tuple[str, ...]
cycles: int
failures: int
max_drawdown: float
governor_verdict: str
crisis_mode: str
symbols: tuple[str, ...] = ()
period: str = ""
interval: str = ""
reliability_score: float | None = None
reliability_observation_seconds: float | None = None
normal_ratio: float | None = None
halt_ratio: float | None = None
mttr_seconds: float | None = None
mtbf_seconds: float | None = None
⋮----
class QualificationStore
⋮----
def load(self) -> QualificationRecord | None
⋮----
payload = json.loads(self.path.read_text(encoding="utf-8"))
⋮----
record = QualificationRecord(
⋮----
temp = self.path.with_suffix(".tmp")
```

## File: ai_trading/qualification_suite.py
```python
@dataclass(frozen=True)
class QualificationCaseResult
⋮----
name: str
soak: SoakResult
qualification: SoakQualification
expected_safe_failure: bool
⋮----
@dataclass(frozen=True)
class QualificationSuiteResult
⋮----
passed: bool
cases: tuple[QualificationCaseResult, ...]
reasons: tuple[str, ...]
⋮----
def _chaos_cases(symbol: str, step: int) -> tuple[tuple[str, tuple[ChaosScenario, ...]], ...]
⋮----
workspace_root = Path(workspace_root)
target_symbol = min(markets)
chaos_step = max(0, min(max_cycles - 1, max_cycles // 2))
⋮----
results: list[QualificationCaseResult] = []
reasons: list[str] = []
⋮----
runtime = isolated_multiasset_runtime(workspace_root / name)
soak = run_multiasset_soak(
qualification = evaluate_soak_qualification(soak)
⋮----
safe_failure = False
⋮----
safe_failure = (
⋮----
baseline_ok = results[0].qualification.passed
chaos_ok = all(case.expected_safe_failure for case in results[1:])
```

## File: ai_trading/quality_store.py
```python
@dataclass
class QualityRecord
⋮----
predictions: list[int]
confidences: list[float]
labels: list[int]
⋮----
class QualityStore
⋮----
def __init__(self, path: str | Path = "artifacts/model_quality.json") -> None
⋮----
def load(self) -> dict[str, QualityRecord]
⋮----
payload = json.loads(self.path.read_text(encoding="utf-8"))
⋮----
def save(self, records: dict[str, QualityRecord]) -> None
⋮----
temp = self.path.with_suffix(".tmp")
⋮----
records = self.load()
record = records.setdefault(key, QualityRecord([], [], []))
```

## File: ai_trading/quantitative_artifact.py
```python
@dataclass(frozen=True)
class QuantitativeQualificationArtifact
⋮----
created_at_utc: str
symbol: str
period: str
interval: str
dataset: DatasetEvidence
config_hash: str
verdict: str
passed_gates: int
total_gates: int
reasons: tuple[str, ...]
benchmark: BenchmarkGateResult
regime: RegimeGateResult
bootstrap: BootstrapGateResult
sensitivity: SensitivityGateResult
cost_stress: CostStressGateResult
evidence_hash: str
⋮----
def _evidence_payload(artifact: QuantitativeQualificationArtifact) -> dict
⋮----
payload = asdict(artifact)
⋮----
canonical = json.dumps(
⋮----
artifact = QuantitativeQualificationArtifact(
⋮----
target = Path(path)
⋮----
temp = target.with_suffix(".tmp")
⋮----
payload = json.loads(target.read_text(encoding="utf-8"))
artifact = QuantitativeQualificationArtifact(**payload)
```

## File: ai_trading/quantitative_qualification.py
```python
@dataclass(frozen=True)
class QuantitativeQualification
⋮----
qualified: bool
passed_gates: int
total_gates: int
reasons: tuple[str, ...]
⋮----
gates = [
⋮----
reasons: list[str] = []
passed = 0
```

## File: ai_trading/readiness_evidence.py
```python
@dataclass(frozen=True)
class ReadinessEvidence
⋮----
performance: PerformanceMetrics
robustness: BootstrapReport
reliability: ReliabilityReport
recovery: RecoveryHealth
data_quality: DataQualityReport
model_quality: ModelQuality
execution: GlobalAllocationReport
⋮----
def _clamp_score(value: float) -> float
⋮----
def performance_component(metrics: PerformanceMetrics) -> float
⋮----
sharpe = _clamp_score((metrics.sharpe / 2.0) * 100.0)
sortino = _clamp_score((metrics.sortino / 2.5) * 100.0)
calmar = _clamp_score((metrics.calmar / 2.0) * 100.0)
drawdown = _clamp_score((1.0 - metrics.max_drawdown / 0.20) * 100.0)
⋮----
def robustness_component(report: BootstrapReport) -> float
⋮----
positive = _clamp_score(report.probability_positive * 100.0)
tail = _clamp_score((1.0 - report.probability_loss_gt_10pct) * 100.0)
p05 = _clamp_score(((report.p05_return + 0.10) / 0.20) * 100.0)
⋮----
def reliability_component(report: ReliabilityReport) -> float
⋮----
def recovery_component(report: RecoveryHealth) -> float
⋮----
score = 100.0
⋮----
score = min(score, 70.0)
⋮----
def data_quality_component(report: DataQualityReport) -> float
⋮----
score = report.score * 100.0
⋮----
def model_stability_component(report: ModelQuality) -> float
⋮----
def execution_quality_component(report: GlobalAllocationReport) -> float
⋮----
cost_ratio = report.estimated_cost / report.expected_return
⋮----
score = min(score, 60.0)
⋮----
def build_readiness_components(evidence: ReadinessEvidence) -> ReadinessComponents
```

## File: ai_trading/readiness_handshake.py
```python
@dataclass(frozen=True)
class ReadinessResult
⋮----
ready: bool
waited_seconds: float
reason: str
⋮----
started = time.monotonic()
⋮----
heartbeat = heartbeat_store.load()
⋮----
elapsed = time.monotonic() - started
```

## File: ai_trading/readiness_release.py
```python
RELEASE_FORMAT_VERSION = "1.0.0"
⋮----
@dataclass(frozen=True)
class ReadinessRelease
⋮----
format_version: str
created_at_utc: str
composite_version: str
composite_score: float
composite_evidence_hash: str
quantitative_evidence_hash: str
readiness_chain_head: str
readiness_chain_records: int
qualification_hash: str
governor_hash: str
resilience_hash: str
trend_status: str
trend_observations: int
trend_score_change: float
release_hash: str
signature_algorithm: str
signature: str
⋮----
@dataclass(frozen=True)
class ReadinessReleaseVerification
⋮----
valid: bool
reason: str = ""
⋮----
def _canonical_hash(payload: object) -> str
⋮----
raw = dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
⋮----
created_at_utc = created_at_utc or datetime.now(UTC).isoformat()
payload = _release_payload(
release_hash = _canonical_hash(payload)
signature_algorithm = "HMAC-SHA256" if signing_key is not None else "NONE"
signature = ""
⋮----
key = signing_key.encode("utf-8") if isinstance(signing_key, str) else signing_key
signature = hmac_new(
⋮----
expected = _canonical_hash(payload)
⋮----
expected_signature = hmac_new(
⋮----
class ReadinessReleaseStore
⋮----
def save(self, release: ReadinessRelease) -> None
⋮----
existing = self.load()
⋮----
temp = self.path.with_suffix(".tmp")
⋮----
def load(self) -> ReadinessRelease | None
⋮----
payload = loads(self.path.read_text(encoding="utf-8"))
```

## File: ai_trading/readiness_revocation.py
```python
@dataclass(frozen=True)
class RevocationRecord
⋮----
release_hash: str
revoked_at_utc: str
reason: str
⋮----
class ReadinessRevocationStore
⋮----
def revoke(self, release_hash: str, *, reason: str) -> RevocationRecord
⋮----
existing = {record.release_hash for record in self.list()}
⋮----
record = RevocationRecord(
⋮----
def is_revoked(self, release_hash: str) -> bool
⋮----
def list(self) -> list[RevocationRecord]
⋮----
records: list[RevocationRecord] = []
```

## File: ai_trading/readiness_score.py
```python
SCORE_VERSION = "1.0.0"
⋮----
@dataclass(frozen=True)
class ReadinessComponents
⋮----
performance: float
robustness: float
reliability: float
recovery: float
data_quality: float
model_stability: float
execution_quality: float
⋮----
@dataclass(frozen=True)
class ReadinessWeights
⋮----
performance: float = 0.20
robustness: float = 0.15
reliability: float = 0.20
recovery: float = 0.10
data_quality: float = 0.10
model_stability: float = 0.15
execution_quality: float = 0.10
⋮----
@dataclass(frozen=True)
class CompositeReadiness
⋮----
version: str
score: float
components: ReadinessComponents
weights: ReadinessWeights
passed: bool
reasons: tuple[str, ...]
evidence_hash: str
⋮----
@dataclass(frozen=True)
class ReadinessPolicy
⋮----
min_score: float = 90.0
min_component: float = 75.0
⋮----
def _bounded(value: float) -> float
⋮----
payload = {
raw = dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
⋮----
weights = weights or ReadinessWeights()
policy = policy or ReadinessPolicy()
⋮----
component_values = {
weight_values = asdict(weights)
total_weight = sum(max(0.0, float(value)) for value in weight_values.values())
⋮----
weighted = sum(
score = weighted / total_weight
⋮----
reasons: list[str] = []
⋮----
normalized = ReadinessComponents(**component_values)
⋮----
@dataclass(frozen=True)
class ReadinessHistoryRecord
⋮----
created_at_utc: str
result: CompositeReadiness
prev_hash: str = ""
record_hash: str = ""
⋮----
@dataclass(frozen=True)
class ReadinessChainReport
⋮----
valid: bool
records: int
legacy_records: int
reason: str = ""
⋮----
class ReadinessHistoryStore
⋮----
def append(self, result: CompositeReadiness) -> ReadinessHistoryRecord
⋮----
previous = self.list()
prev_hash = previous[-1].record_hash if previous else ""
created_at_utc = datetime.now(UTC).isoformat()
⋮----
canonical = dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
record_hash = sha256(canonical).hexdigest()
record = ReadinessHistoryRecord(
⋮----
def list(self) -> list[ReadinessHistoryRecord]
⋮----
records: list[ReadinessHistoryRecord] = []
⋮----
payload = loads(line)
result_payload = payload["result"]
result = CompositeReadiness(
⋮----
def verify_chain(self) -> ReadinessChainReport
⋮----
previous_hash = ""
records = 0
legacy_records = 0
⋮----
record_hash = payload.get("record_hash", "")
prev_hash = payload.get("prev_hash", "")
⋮----
canonical_payload = dict(payload)
⋮----
canonical = dumps(
expected = sha256(canonical).hexdigest()
⋮----
previous_hash = record_hash
```

## File: ai_trading/readiness_trend.py
```python
@dataclass(frozen=True)
class ReadinessTrendPolicy
⋮----
window: int = 5
max_decline: float = 5.0
min_pass_ratio: float = 0.80
⋮----
@dataclass(frozen=True)
class ReadinessTrend
⋮----
status: str
observations: int
latest_score: float | None
score_change: float
pass_ratio: float
reasons: tuple[str, ...]
⋮----
policy = policy or ReadinessTrendPolicy()
recent = records[-policy.window :]
⋮----
scores = [record.result.score for record in recent]
score_change = scores[-1] - scores[0] if len(scores) > 1 else 0.0
pass_ratio = sum(record.result.passed for record in recent) / len(recent)
⋮----
reasons: list[str] = []
```

## File: ai_trading/readiness.py
```python
@dataclass(frozen=True)
class ReadinessPolicy
⋮----
min_burn_in_bars: int = 126
min_sharpe: float = 0.75
min_sortino: float = 1.00
max_drawdown: float = 0.10
min_total_return: float = 0.0
min_positive_bootstrap_probability: float = 0.65
min_regimes_covered: int = 2
max_consecutive_scheduler_errors: int = 0
⋮----
@dataclass(frozen=True)
class ReadinessCheck
⋮----
name: str
passed: bool
value: float | int
threshold: float | int
comparison: str
⋮----
@dataclass(frozen=True)
class ReadinessReport
⋮----
ready: bool
checks_passed: int
checks_total: int
reasons: tuple[str, ...]
checks: tuple[ReadinessCheck, ...] = ()
⋮----
policy = policy or ReadinessPolicy()
checks = (
⋮----
reason_by_name = {
failures = [reason_by_name[check.name] for check in checks if not check.passed]
passed = sum(check.passed for check in checks)
```

## File: ai_trading/recovery_health.py
```python
@dataclass(frozen=True)
class RecoveryHealthPolicy
⋮----
max_recent_failures: int = 2
max_fallback_depth: int = 2
recent_event_window: int = 20
⋮----
@dataclass(frozen=True)
class RecoveryHealth
⋮----
status: str
recent_attempts: int
recent_failures: int
max_fallback_depth: int
reasons: tuple[str, ...]
⋮----
policy = policy or RecoveryHealthPolicy()
events = [
recent = events[-policy.recent_event_window :]
recent_failures = sum(event.event == "recovery_failed" for event in recent)
max_depth = max(
⋮----
reasons: list[str] = []
```

## File: ai_trading/recovery.py
```python
@dataclass(frozen=True)
class RecoveryResult
⋮----
restored: bool
snapshot: str | None
reason: str
verified: bool = False
mismatches: tuple[str, ...] = ()
candidates_tested: int = 0
fallback_depth: int = 0
⋮----
candidates = snapshot_store.valid_snapshots()
⋮----
restored = snapshot_store.restore_snapshot(candidates[0], destination_root)
⋮----
last_reason = "no logically consistent snapshot available"
last_mismatches: tuple[str, ...] = ()
last_snapshot: str | None = None
⋮----
tracked_paths = [Path(path) for path in state_files]
⋮----
temp_dir = Path(temp_dir_name)
backups: dict[Path, Path | None] = {}
⋮----
backup = temp_dir / f"{index}.bak"
⋮----
restored = snapshot_store.restore_snapshot(candidate, destination_root)
verification = verify_checkpoint_state(
⋮----
last_reason = verification.reason
last_mismatches = verification.mismatches
last_snapshot = str(restored)
⋮----
restore_temp = path.with_suffix(path.suffix + ".rollback.tmp")
```

## File: ai_trading/regime_gate.py
```python
@dataclass(frozen=True)
class RegimeGatePolicy
⋮----
min_observed_regimes: int = 2
min_regime_return: float = -0.10
max_regime_return_spread: float = 0.50
⋮----
@dataclass(frozen=True)
class RegimeGateResult
⋮----
passed: bool
observed_regimes: int
worst_regime: str | None
worst_return: float | None
return_spread: float
reasons: tuple[str, ...]
⋮----
policy = policy or RegimeGatePolicy()
returns = report.regime_returns
reasons: list[str] = []
⋮----
worst_regime = min(returns, key=returns.get) if returns else None
worst_return = returns[worst_regime] if worst_regime is not None else None
⋮----
spread = max(returns.values()) - min(returns.values()) if returns else 0.0
```

## File: ai_trading/regime_validation.py
```python
@dataclass(frozen=True)
class RegimeValidation
⋮----
valid: bool
covered_regimes: int
profitable_regimes: int
worst_regime_return: float
reason: str
⋮----
profitable = sum(v > 0 for v in regime_returns.values())
fraction = profitable / len(regime_returns)
worst = min(regime_returns.values())
```

## File: ai_trading/regime.py
```python
@dataclass(frozen=True)
class MarketRegime
⋮----
trend: str
volatility: str
⋮----
@property
    def name(self) -> str
⋮----
def detect_regime(row: pd.Series) -> MarketRegime
⋮----
trend_10 = float(row.get("trend_10", 0.0))
trend_30 = float(row.get("trend_30", 0.0))
vol_10 = float(row.get("vol_10", 0.0))
⋮----
trend_score = 0.6 * trend_10 + 0.4 * trend_30
⋮----
trend = "bull"
⋮----
trend = "bear"
⋮----
trend = "sideways"
⋮----
volatility = "high_vol" if vol_10 >= 0.02 else "normal_vol"
```

## File: ai_trading/reliability.py
```python
@dataclass(frozen=True)
class ReliabilityReport
⋮----
observation_seconds: float
normal_ratio: float
cautious_ratio: float
degraded_ratio: float
recovery_ratio: float
cooldown_ratio: float
halt_ratio: float
halt_count: int
incident_count: int
mttr_seconds: float | None
mtbf_seconds: float | None
reliability_score: float
⋮----
now_utc = now_utc or datetime.now(UTC)
events = [
⋮----
parsed: list[tuple[datetime, str, str]] = []
⋮----
timestamp = datetime.fromisoformat(event.created_at_utc)
⋮----
timestamp = timestamp.replace(tzinfo=UTC)
⋮----
durations = {
⋮----
ended = parsed[index + 1][0] if index + 1 < len(parsed) else now_utc
⋮----
observation = sum(durations.values())
ratios = {
⋮----
halt_count = sum(to_mode == "HALT" for _, _, to_mode in parsed)
incident_starts: list[datetime] = []
recoveries: list[float] = []
open_incident: datetime | None = None
⋮----
open_incident = timestamp
⋮----
open_incident = None
⋮----
mttr = sum(recoveries) / len(recoveries) if recoveries else None
gaps = [
mtbf = sum(gaps) / len(gaps) if gaps else None
⋮----
penalty = (
score = max(0.0, min(100.0, 100.0 - penalty))
```

## File: ai_trading/replay.py
```python
@dataclass(frozen=True)
class ReplayEvent
⋮----
event: str
payload: dict[str, Any]
⋮----
@dataclass(frozen=True)
class ReplayReport
⋮----
events: tuple[ReplayEvent, ...]
deterministic: bool
compared_events: int
⋮----
events: list[ReplayEvent] = []
path = Path(path)
⋮----
record = json.loads(line)
event = str(record.get("event", ""))
⋮----
payload = record.get("payload", {})
⋮----
compared = min(len(left), len(right))
deterministic = len(left) == len(right)
⋮----
deterministic = False
```

## File: ai_trading/reproducibility.py
```python
@dataclass(frozen=True)
class ReproducibilityVerification
⋮----
valid: bool
reasons: tuple[str, ...]
⋮----
"""Fail closed when current inputs cannot reproduce artifact identity."""
failures: list[str] = []
⋮----
expected = artifact.dataset
current = build_dataset_evidence(
⋮----
"""Convenience predicate for exact market-data identity."""
```

## File: ai_trading/research_model_codec.py
```python
"""Versioned River-v2 research codec, isolated from paper production storage.

This module is opt-in for offline and read-only shadow studies only.
The production model_codec continues to accept *only* joblib-river-v1.
Joblib deserialization is unsafe for untrusted payloads; only load artifacts
from a trusted research run, never remote or user-supplied model blobs.
"""
⋮----
RESEARCH_MODEL_FORMAT = "joblib-river-ovr-v2"
RESEARCH_MODEL_VERSION = 2
⋮----
def serialize_research_model(model: RiverMulticlassDirectionModel) -> ModelBlob
⋮----
"""Serialize a ternary River challenger without using the production codec."""
⋮----
buffer = BytesIO()
⋮----
payload = buffer.getvalue()
⋮----
def deserialize_research_model(blob: ModelBlob) -> RiverMulticlassDirectionModel
⋮----
"""Load only a trusted, versioned v2 challenger blob; never accept v1."""
⋮----
model = joblib.load(BytesIO(blob.payload))
```

## File: ai_trading/resilience_stability.py
```python
@dataclass(frozen=True)
class ResilienceStabilityPolicy
⋮----
event_window: int = 30
max_oscillations: int = 4
max_recovery_streak_events: int = 6
max_cooldowns: int = 3
⋮----
@dataclass(frozen=True)
class ResilienceStability
⋮----
status: str
oscillations: int
recovery_streak_events: int
cooldown_count: int
reasons: tuple[str, ...]
⋮----
policy = policy or ResilienceStabilityPolicy()
events = [
⋮----
modes = [str(event.metadata.get("to_mode", "")) for event in events]
oscillations = 0
⋮----
recovery_streak = (
⋮----
cooldown_count = sum(mode == "COOLDOWN" for mode in modes)
⋮----
reasons: list[str] = []
⋮----
severe = (
status = "critical" if severe else "degraded" if reasons else "stable"
```

## File: ai_trading/resilience.py
```python
@dataclass(frozen=True)
class ResiliencePolicy
⋮----
recovery_confirmations: int = 3
cooldown_confirmations: int = 3
halt_recovery_failures: int = 4
halt_recovery_fallback_depth: int = 5
cautious_exposure_cap: float = 0.75
degraded_exposure_cap: float = 0.35
recovery_exposure_cap: float = 0.50
cooldown_exposure_cap: float = 0.25
⋮----
@dataclass(frozen=True)
class ResilienceContext
⋮----
data_quality: float = 1.0
drawdown: float = 0.0
annualized_volatility: float = 0.0
recent_incidents: int = 0
⋮----
severity = 0
⋮----
@dataclass(frozen=True)
class ResilienceState
⋮----
mode: str = "NORMAL"
healthy_streak: int = 0
reason: str = "initial state"
mode_steps: int = 0
instability_status: str = "stable"
⋮----
@dataclass(frozen=True)
class ResilienceSignals
⋮----
governor_verdict: str
crisis_mode: str
recovery_degraded: bool
recovery_recent_failures: int
recovery_fallback_depth: int
⋮----
@dataclass(frozen=True)
class ResilienceDecision
⋮----
state: ResilienceState
exposure_cap: float
promotions_allowed: bool
scheduler_allowed: bool
⋮----
class ResilienceStateStore
⋮----
def __init__(self, path: str | Path = "artifacts/resilience_state.json") -> None
⋮----
def load(self) -> ResilienceState
⋮----
def save(self, state: ResilienceState) -> None
⋮----
temp = self.path.with_suffix(".tmp")
⋮----
policy = policy or ResiliencePolicy()
⋮----
critical = (
degraded = (
cautious = (
healthy = (
⋮----
state = ResilienceState(
⋮----
streak = current.healthy_streak + 1 if healthy else 0
⋮----
next_mode = "DEGRADED" if degraded else "CAUTIOUS"
⋮----
streak = current.healthy_streak + 1
⋮----
limits = {
```

## File: ai_trading/restart_log.py
```python
@dataclass(frozen=True)
class RestartEvent
⋮----
timestamp_utc: str
exit_code: int | None
runtime_seconds: float
restart_index: int
reason: str
⋮----
class RestartLog
⋮----
def __init__(self, path: str | Path = "artifacts/restarts.jsonl") -> None
⋮----
event = RestartEvent(
```

## File: ai_trading/risk_governor.py
```python
@dataclass(frozen=True)
class GovernorPolicy
⋮----
min_data_quality: float = 0.95
halt_data_quality: float = 0.75
min_model_confidence: float = 0.55
flatten_drawdown: float = 0.15
reduce_drawdown: float = 0.08
max_stressed_cvar: float = 0.08
reduce_stressed_cvar: float = 0.05
halt_recovery_failures: int = 4
halt_recovery_fallback_depth: int = 5
degraded_recovery_exposure_scale: float = 0.35
⋮----
@dataclass(frozen=True)
class GovernorSignals
⋮----
data_quality: float
system_healthy: bool
model_confidence: float
portfolio_risk_approved: bool
stress_approved: bool
stressed_cvar: float
drawdown: float
crisis_mode: str
liquidity_stressed: bool = False
recovery_degraded: bool = False
recovery_recent_failures: int = 0
recovery_fallback_depth: int = 0
⋮----
@dataclass(frozen=True)
class GovernorDecision
⋮----
verdict: str
exposure_scale: float
allow_rebalance: bool
flatten: bool
halt: bool
reason: str
⋮----
policy = policy or GovernorPolicy()
```

## File: ai_trading/risk.py
```python
@dataclass(frozen=True)
class PortfolioSnapshot
⋮----
equity: float
peak_equity: float
day_start_equity: float
current_position_value: float = 0.0
⋮----
@dataclass(frozen=True)
class RiskDecision
⋮----
approved: bool
side: int
target_notional: float
reason: str
⋮----
class RiskEngine
⋮----
def __init__(self, config: RiskConfig) -> None
⋮----
def evaluate(self, prediction: Prediction, portfolio: PortfolioSnapshot) -> RiskDecision
⋮----
drawdown = 1.0 - portfolio.equity / max(portfolio.peak_equity, portfolio.equity)
⋮----
daily_loss = 1.0 - portfolio.equity / max(portfolio.day_start_equity, portfolio.equity)
⋮----
confidence_scale = min(1.0, max(0.0, (prediction.confidence - 0.5) / 0.5))
target = (
```

## File: ai_trading/river_v2_shadow.py
```python
"""Opt-in River-v2 forward observer and delayed, audit-only label comparison.

Neither the observer nor its quality calculation can place or approve trades.
A forward observation is never given future market candles or future labels.
"""
⋮----
_INTERVAL = pd.Timedelta(minutes=5)
⋮----
@dataclass(frozen=True)
class RiverV2ForwardObservation
⋮----
prediction: Prediction
signal_time: str
signal_close: float
observed_at_utc: str
training_rows: int
training_end: str
horizon_bars: int
return_threshold: float
min_confidence: float
gated_side: int
model_format: str = RESEARCH_MODEL_FORMAT
model_version: int = RESEARCH_MODEL_VERSION
⋮----
@dataclass(frozen=True)
class RiverV2ForwardComparison
⋮----
observations: int
pending: int
short_predictions: int
river: ModelQuality
river_v2: ModelQuality
⋮----
@property
    def score_delta(self) -> float | None
⋮----
"""Predict only from the latest *completed, recent* five-minute signal.

    The current market's last row must be a fully closed candle. The next
    candle is not present. Older/catch-up observations are deliberately
    skipped to avoid representing retrospective predictions as forward ones.
    """
⋮----
signal_time = pd.Timestamp(market.index[-1])
⋮----
signal_utc = signal_time.tz_convert("UTC")
current = pd.Timestamp(now or datetime.now(UTC))
⋮----
current = current.tz_convert("UTC")
age = current - (signal_utc + _INTERVAL)
# Allow a short provider delay, but never score signals observed after
# their next five-minute outcome could already have completed.
⋮----
# Slice first: even accidental future columns cannot reach the trainer.
observed = market.iloc[:].copy()
features = make_features(observed)
labels = make_labels(
last_train_pos = len(observed) - 1 - horizon_bars
⋮----
candidates = [
⋮----
signal_row = features.iloc[-1].loc[FEATURES]
⋮----
train_positions = candidates[-max_train_rows:]
model = RiverMulticlassDirectionModel()
⋮----
prediction = model.predict_one(signal_row)
⋮----
return None  # Fail open for paper execution, closed for shadow evidence.
signal_close = float(observed["Close"].iloc[-1])
⋮----
# The prediction must still be timely AFTER inference has completed.
# A slow CPU/research run must not backdate evidence to its start time.
completed_at = current if now is not None else pd.Timestamp(datetime.now(UTC))
⋮----
"""Evaluate only matured, matched v1/v2 signals stored on different cycles.

    v2 predictions were committed in an earlier audit row. The v1
    `execution_close` and v1 prediction arrive in a later audit row.
    The comparison is directional accuracy, NOT a tradable return backtest.
    """
audit_rows = tuple(payloads)
v1_by_signal: dict[str, dict[str, Any]] = {}
⋮----
signal = payload.get("signal_time")
⋮----
sides_v1: list[int] = []
conf_v1: list[float] = []
sides_v2: list[int] = []
conf_v2: list[float] = []
labels: list[int] = []
pending = 0
shorts = 0
seen: set[str] = set()
⋮----
shadow = payload.get("river_v2_shadow")
⋮----
signal = shadow.get("signal_time")
⋮----
later = v1_by_signal.get(signal)
⋮----
continue  # This matching is defined for one-bar outcomes only.
signal_time = pd.Timestamp(signal)
execution_time = pd.Timestamp(later["execution_time"])
observed_time = pd.Timestamp(shadow["observed_at_utc"])
committed_time = pd.Timestamp(payload["_audit_timestamp_utc"])
⋮----
signal_time = signal_time.tz_convert("UTC")
execution_time = execution_time.tz_convert("UTC")
observed_time = observed_time.tz_convert("UTC")
committed_time = committed_time.tz_convert("UTC")
⋮----
continue  # No imputed result across session/provider gaps.
⋮----
continue  # Must have been observed before the outcome closed.
⋮----
continue  # Must also have been DURABLY audited before outcome closed.
signal_close = float(shadow["signal_close"])
next_close = float(later["execution_close"])
threshold = float(shadow["return_threshold"])
⋮----
v1 = later["prediction"]
v2 = shadow["prediction"]
⋮----
minimum = float(shadow["min_confidence"])
⋮----
realized_return = next_close / signal_close - 1.0
label = int(realized_return > threshold) - int(realized_return < -threshold)
# Compare identical raw side/confidence definitions for both models.
# Minimum confidence applies only to the separate directional count.
⋮----
def quality(sides: list[int], confidences: list[float]) -> ModelQuality
```

## File: ai_trading/robustness.py
```python
@dataclass(frozen=True)
class BootstrapReport
⋮----
median_return: float
p05_return: float
p95_return: float
probability_positive: float
probability_loss_gt_10pct: float
⋮----
clean = equity.astype(float).dropna()
returns = clean.pct_change().dropna().to_numpy(dtype=float)
⋮----
rng = np.random.default_rng(random_state)
n = len(returns)
possible = max(1, n - block_size + 1)
outcomes = np.empty(simulations, dtype=float)
⋮----
sampled: list[float] = []
⋮----
start = int(rng.integers(0, possible))
⋮----
path = np.asarray(sampled[:n], dtype=float)
```

## File: ai_trading/runtime_factory.py
```python
def isolated_multiasset_runtime(root: str | Path) -> MultiAssetPaperRuntime
⋮----
root = Path(root)
```

## File: ai_trading/runtime_lock.py
```python
class RuntimeLock
⋮----
def __init__(self, path: str | Path = "artifacts/runtime.lock") -> None
⋮----
def __enter__(self) -> Self
⋮----
def __exit__(self, exc_type, exc, tb) -> None
```

## File: ai_trading/runtime_state.py
```python
@dataclass
class RuntimeState
⋮----
cash: float
units: float
last_price: float
peak_equity: float
day_start_equity: float
average_entry_price: float = 0.0
last_processed: str | None = None
processed_bars: int = 0
last_learning_cycle_bar: int = 0
⋮----
class RuntimeStateStore
⋮----
def __init__(self, path: str | Path = "artifacts/runtime_state.json") -> None
⋮----
def load(self, starting_cash: float) -> RuntimeState
⋮----
def save(self, state: RuntimeState) -> None
⋮----
temp = self.path.with_suffix(".tmp")
```

## File: ai_trading/runtime_status.py
```python
@dataclass(frozen=True)
class HostedRuntimeStatus
⋮----
engine_status: str
symbol: str
interval: str
updated_at_utc: str
last_cycle_timestamp: str | None = None
processed: bool = False
side: int = 0
confidence: float = 0.0
approved: bool = False
reason: str = ""
equity: float = 0.0
units: float = 0.0
processed_bars: int = 0
error: str | None = None
poll_seconds: float = 60.0
consecutive_cycle_errors: int = 0
cycle_duration_seconds: float | None = None
mtf_evaluated: bool = False
decision_reason: str | None = None
⋮----
current_time = now or datetime.now(UTC)
⋮----
current_time = current_time.replace(tzinfo=UTC)
⋮----
current_time = current_time.astimezone(UTC)
⋮----
stale_after_seconds = max(30.0, status.poll_seconds * 3.0)
heartbeat_age_seconds: float | None
heartbeat_stale = False
⋮----
heartbeat_time = datetime.fromisoformat(status.updated_at_utc)
⋮----
heartbeat_time = heartbeat_time.replace(tzinfo=UTC)
⋮----
heartbeat_time = heartbeat_time.astimezone(UTC)
heartbeat_age_seconds = max(
heartbeat_stale = heartbeat_age_seconds > stale_after_seconds
⋮----
heartbeat_age_seconds = None
heartbeat_stale = True
⋮----
engine_status = status.engine_status
⋮----
engine_status = "STALE"
⋮----
payload: dict[str, object] = asdict(status)
⋮----
class HostedRuntimeStatusStore
⋮----
def __init__(self, path: str | Path = "artifacts/runtime_status.json") -> None
⋮----
def load(self) -> HostedRuntimeStatus | None
⋮----
def save(self, status: HostedRuntimeStatus) -> None
⋮----
temp = self.path.with_suffix(".tmp")
```

## File: ai_trading/runtime.py
```python
@dataclass(frozen=True)
class RuntimeStepResult
⋮----
processed: bool
timestamp: str | None
side: int
confidence: float
approved: bool
reason: str
equity: float
units: float
processed_bars: int
retrain_due: bool
⋮----
@dataclass(frozen=True)
class PreparedRuntimeMarket
⋮----
market: pd.DataFrame
features: pd.DataFrame
labels: pd.Series
valid: pd.Index
eligible: tuple[object, ...]
⋮----
class PaperAutonomousRuntime
⋮----
"""One-step autonomous paper runtime.

    A scheduler may call step repeatedly. The runtime itself never routes
    real orders and never bypasses the independent risk engine.
    """
⋮----
base_risk_config = risk_config or RiskConfig()
⋮----
# Honor an explicit lock path, including legacy single-runtime callers.
⋮----
# Parallel markets must not contend for the same process-wide file.
# The same durable runtime key still gets an identical lock path,
# while PostgreSQL revision checks protect commits across hosts.
digest = hashlib.sha256(self.runtime_key.encode("utf-8")).hexdigest()
⋮----
def _broker_from_state(self, state: RuntimeState) -> PaperBroker
⋮----
broker = PaperBroker(self.risk_config)
⋮----
features = make_features(df)
valid = features.dropna().index
⋮----
execution: list[object] = []
# Keep one valid row in reserve exactly as the legacy latest-bar path did.
# A targeted signal also needs one prior valid row for online learning.
⋮----
signal_pos = int(df.index.get_loc(signal_idx))
⋮----
def _eligible_execution_indices(self, df: pd.DataFrame) -> tuple[object, ...]
⋮----
def prepare_market(self, df: pd.DataFrame) -> PreparedRuntimeMarket
⋮----
labels = make_labels(
⋮----
def step(self, df: pd.DataFrame) -> RuntimeStepResult
⋮----
prepared = self.prepare_market(df)
⋮----
def step_at(self, df: pd.DataFrame, execution_idx: object) -> RuntimeStepResult
⋮----
prepared = PreparedRuntimeMarket(
⋮----
df = prepared.market
features = prepared.features
labels = prepared.labels
valid = prepared.valid
eligible = prepared.eligible
⋮----
execution_pos = int(df.index.get_loc(execution_idx))
⋮----
signal_idx = df.index[execution_pos - 1]
valid_positions = {value: index for index, value in enumerate(valid)}
signal_valid_pos = valid_positions.get(signal_idx)
⋮----
learn_idx = valid[signal_valid_pos - 1]
⋮----
execution_time = str(execution_idx)
persisted = self.persistence.load_runtime(
state = persisted.state
⋮----
eligible_positions = {str(value): index for index, value in enumerate(eligible)}
target_position = eligible_positions[execution_time]
persisted_position = (
⋮----
broker = self._broker_from_state(state)
⋮----
model = RiverDirectionModel()
⋮----
model = deserialize_model(persisted.model)
⋮----
learn_label = labels.get(learn_idx)
⋮----
row = features.loc[signal_idx, FEATURES]
observed_regime = detect_regime(row).name
prediction: Prediction = model.predict_one(row)
⋮----
execution_price = float(df.at[execution_idx, "Open"])
close_price = float(df.at[execution_idx, "Close"])
⋮----
execution_day = pd.Timestamp(execution_idx).date()
previous_day = (
⋮----
snapshot = PortfolioSnapshot(
decision = self.risk.evaluate(prediction, snapshot)
⋮----
trade: TradeSnapshot | None = None
previous_units = broker.state.units
⋮----
fill = broker.rebalance(
delta_units = broker.state.units - previous_units
⋮----
trade = TradeSnapshot(
⋮----
processed_bars = state.processed_bars + 1
bars_since_cycle = processed_bars - state.last_learning_cycle_bar
retrain_due = bars_since_cycle >= self.learning_cycle_every_bars
⋮----
new_state = self._state_from_broker(
audit_payload = {
⋮----
outcome = self.persistence.commit_step(
```

## File: ai_trading/scheduler_endpoint.py
```python
@dataclass(frozen=True)
class SchedulerHttpResponse
⋮----
status_code: int
payload: dict[str, object]
⋮----
_ALLOWED_SCHEDULER_SOURCES = {"cloudflare", "github"}
_SCHEDULER_FRESHNESS_SECONDS = 32 * 60
⋮----
normalized_source = (source or "").strip().lower()
⋮----
normalized_source = "external"
⋮----
payload: dict[str, object] = {
processed = response.payload.get("processed")
⋮----
processed_bars = response.payload.get("processed_bars")
⋮----
remaining_backlog = response.payload.get("remaining_backlog")
⋮----
mtf_evaluated = response.payload.get("mtf_evaluated")
⋮----
partial_failure = response.payload.get("partial_failure")
⋮----
failed_markets = response.payload.get("failed_markets")
⋮----
def _utc_now(now: datetime | None) -> datetime
⋮----
current = now or datetime.now(UTC)
⋮----
timestamp = datetime.fromisoformat(timestamp_utc)
⋮----
timestamp = timestamp.replace(tzinfo=UTC)
⋮----
timestamp = timestamp.astimezone(UTC)
age = (now - timestamp).total_seconds()
⋮----
consecutive_cloudflare_successes = 0
⋮----
latest = deliveries[-1] if deliveries else None
current = _utc_now(now)
latest_age_seconds = (
cloudflare_delivery_fresh = bool(
⋮----
def _authorized(authorization: str | None, configured_token: str) -> bool
⋮----
provided = authorization.removeprefix("Bearer ")
⋮----
result = run_cycle()
```

## File: ai_trading/scheduler_fallback.py
```python
"""Authenticated GitHub scheduler fallback using Render as the single DB writer.

The dashboard owns the Neon connection; GitHub never receives database credentials.
"""
⋮----
class FallbackFailure(RuntimeError)
⋮----
"""Sanitized failure suitable for public CI logs."""
⋮----
_CLOUDFLARE_HEALTHY_WINDOW_SECONDS = 32 * 60
⋮----
def _recent_cloudflare(payload: object) -> bool
⋮----
age = payload.get("last_delivery_age_seconds")
⋮----
"""Skip a recent successful Cloudflare cycle, or trigger one paper-only cycle."""
⋮----
origin = base_url.rstrip("/")
status_request = Request(
# Do not spend the execution budget waiting on optional scheduler telemetry.
# Allow a slower cold-starting Render service to complete the actual cycle.
status_timeout = min(timeout, 45.0)
⋮----
status_payload = (
⋮----
status_payload = None
⋮----
cycle_request = Request(
⋮----
body = response.read(16_385)
⋮----
payload = json.loads(body)
⋮----
def main() -> int
⋮----
parser = argparse.ArgumentParser(description="Neon-budgeted paper scheduler fallback")
⋮----
args = parser.parse_args()
⋮----
outcome = run_fallback(
```

## File: ai_trading/scheduler.py
```python
@dataclass(frozen=True)
class SchedulerConfig
⋮----
poll_seconds: float = 60.0
max_iterations: int | None = None
max_consecutive_errors: int = 5
error_backoff_seconds: float = 5.0
max_error_backoff_seconds: float = 300.0
max_governor_halts: int = 3
run_health_check: bool = True
⋮----
class PaperScheduler
⋮----
def _audit_error(self, exc: Exception, consecutive_errors: int) -> None
⋮----
runtime = getattr(self.orchestrator, "runtime", None)
audit = getattr(runtime, "audit", None)
⋮----
def run(self) -> list[OrchestrationResult]
⋮----
results: list[OrchestrationResult] = []
iteration = 0
consecutive_errors = 0
⋮----
governor_state = self.governor_state_store.load()
⋮----
started = monotonic()
⋮----
df = self.data_loader()
⋮----
result = self.orchestrator.step(df, symbol=self.symbol)
⋮----
result = self.orchestrator.step(
⋮----
delay = min(
⋮----
elapsed = monotonic() - started
```

## File: ai_trading/sensitivity_gate.py
```python
@dataclass(frozen=True)
class SensitivityGatePolicy
⋮----
min_pass_ratio: float = 0.67
min_excess_return: float = -0.05
min_sharpe: float = 0.0
max_drawdown: float = 0.30
⋮----
@dataclass(frozen=True)
class SensitivityGateResult
⋮----
passed: bool
scenarios: int
passing_scenarios: int
pass_ratio: float
worst_excess_return: float
worst_sharpe: float
worst_drawdown: float
reasons: tuple[str, ...]
⋮----
policy = policy or SensitivityGatePolicy()
⋮----
passing = [
ratio = len(passing) / len(results)
reasons: list[str] = []
⋮----
worst_excess = min(result.excess_return for result in results)
worst_sharpe = min(result.sharpe for result in results)
worst_drawdown = max(result.max_drawdown for result in results)
```

## File: ai_trading/session_integrity.py
```python
@dataclass(frozen=True)
class SessionFingerprint
⋮----
fingerprint: str
state_hashes: dict[str, str]
audit_tail_hash: str
⋮----
def _audit_tail_hash(path: Path) -> str
⋮----
last = ""
⋮----
last = line
⋮----
record = json.loads(last)
⋮----
hashes = {
audit_tail = _audit_tail_hash(Path(audit_path))
payload = {
canonical = json.dumps(
digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
```

## File: ai_trading/shadow_challenger.py
```python
@dataclass(frozen=True)
class ShadowChallengerResult
⋮----
prediction: Prediction
regime: str
signal_time: str
execution_time: str
training_rows: int
training_end: str
realized_label: int | None
⋮----
"""Evaluate a batch ensemble without allowing it to influence execution.

    Training rows are restricted so every training label is fully observable by
    the signal bar. This keeps the challenger suitable for shadow evaluation
    during paper trading and catch-up processing.
    """
⋮----
execution_pos = int(market.index.get_loc(execution_idx))
⋮----
signal_pos = execution_pos - 1
signal_idx = market.index[signal_pos]
⋮----
challenger_features = make_challenger_features(market)
⋮----
signal_row = challenger_features.loc[signal_idx, CHALLENGER_FEATURES]
⋮----
last_train_pos = signal_pos - horizon_bars
⋮----
allowed = set(market.index[: last_train_pos + 1])
valid_feature_rows = challenger_features.loc[:, CHALLENGER_FEATURES].dropna().index
labeled_rows = labels.dropna().index
train_idx = [
⋮----
model = EnsembleDirectionModel(
⋮----
regime = detect_regime(signal_row)
prediction = model.predict_one(signal_row, regime)
realized = labels.get(signal_idx)
realized_label = int(realized) if pd.notna(realized) else None
```

## File: ai_trading/shadow_promotion_gate.py
```python
@dataclass(frozen=True)
class ShadowPromotionPolicy
⋮----
min_observations: int = 250
min_score_delta: float = 0.02
min_accuracy_delta: float = 0.0
max_brier_increase: float = 0.02
min_directional_edge_delta: float = 0.0
⋮----
@dataclass(frozen=True)
class ShadowPromotionGate
⋮----
eligible_for_review: bool
reasons: tuple[str, ...]
observations: int
score_delta: float
accuracy_delta: float
brier_delta: float
directional_edge_delta: float
⋮----
policy = policy or ShadowPromotionPolicy()
reasons: list[str] = []
⋮----
score_delta = float(comparison.challenger.score - comparison.river.score)
accuracy_delta = float(
brier_delta = float(comparison.challenger.brier - comparison.river.brier)
directional_edge_delta = float(
```

## File: ai_trading/shadow_quality.py
```python
@dataclass(frozen=True)
class ShadowQualityComparison
⋮----
observations: int
river: ModelQuality
challenger: ModelQuality
⋮----
@property
    def score_delta(self) -> float
⋮----
def _empty_quality() -> ModelQuality
⋮----
river_sides: list[int] = []
river_confidences: list[float] = []
challenger_sides: list[int] = []
challenger_confidences: list[float] = []
labels: list[int] = []
⋮----
shadow = payload.get("shadow_challenger")
river_prediction = payload.get("prediction")
⋮----
challenger_prediction = shadow.get("prediction")
realized = shadow.get("realized_label")
⋮----
river_side = int(river_prediction["side"])
river_confidence = float(river_prediction["confidence"])
challenger_side = int(challenger_prediction["side"])
challenger_confidence = float(challenger_prediction["confidence"])
label = int(realized)
⋮----
observations = len(labels)
⋮----
empty = _empty_quality()
⋮----
index = pd.RangeIndex(observations)
realized = pd.Series(labels, index=index, dtype="int64")
river = evaluate_model_quality(
challenger = evaluate_model_quality(
```

## File: ai_trading/soak_gate.py
```python
@dataclass(frozen=True)
class SoakQualificationPolicy
⋮----
min_cycles: int = 50
min_success_ratio: float = 0.98
max_failures: int = 2
max_drawdown: float = 0.10
min_duration_seconds: float = 0.0
disallowed_governor_verdicts: tuple[str, ...] = ("HALT",)
⋮----
@dataclass(frozen=True)
class SoakQualification
⋮----
passed: bool
success_ratio: float
reasons: tuple[str, ...]
⋮----
policy = policy or SoakQualificationPolicy()
reasons: list[str] = []
⋮----
success_ratio = (
```

## File: ai_trading/soak.py
```python
@dataclass(frozen=True)
class SoakResult
⋮----
cycles: int
successes: int
failures: int
final_equity: float | None
governor_verdict: str
crisis_mode: str
errors: tuple[str, ...]
max_drawdown: float = 0.0
min_equity: float | None = None
started_at_utc: str | None = None
completed_at_utc: str | None = None
duration_seconds: float = 0.0
⋮----
min_length = min(len(df) for df in markets.values())
⋮----
total_possible = min_length - start_bars
cycles = total_possible if max_cycles is None else min(total_possible, max_cycles)
⋮----
started_at = datetime.now(UTC)
successes = 0
failures = 0
errors: list[str] = []
final_equity: float | None = None
peak_equity: float | None = None
⋮----
max_drawdown = 0.0
⋮----
end = start_bars + offset + 1
window = {
⋮----
window = apply_chaos(
⋮----
result = runtime.step(window)
final_equity = result.equity
peak_equity = (
min_equity = (
⋮----
max_drawdown = max(
⋮----
governor = runtime.governor_state_store.load()
crisis = runtime.crisis_state_store.load()
⋮----
completed_at = datetime.now(UTC)
```

## File: ai_trading/specialist_experts.py
```python
@dataclass(frozen=True)
class SpecialistSpec
⋮----
name: str
target_regimes: tuple[str, ...]
⋮----
class SpecialistDirectionModel
⋮----
def __init__(self, kind: str, random_state: int = 42) -> None
⋮----
def fit(self, x: pd.DataFrame, y: pd.Series) -> None
⋮----
x2 = x.loc[:, FEATURES].dropna()
y2 = y.reindex(x2.index).dropna().astype(int)
x2 = x2.loc[y2.index]
⋮----
def supports(self, regime: MarketRegime) -> bool
⋮----
def predict_one(self, row: pd.Series) -> Prediction
⋮----
x = pd.DataFrame([row.loc[FEATURES].astype(float).to_dict()])
proba = self.model.predict_proba(x)[0]
mapping = {
⋮----
side = max(mapping, key=mapping.get)
```

## File: ai_trading/startup_check.py
```python
@dataclass(frozen=True)
class StartupCheckReport
⋮----
ready: bool
reasons: tuple[str, ...]
snapshot_available: bool
audit_valid: bool
state_files_valid: bool
jsonl_files_valid: bool
active_artifact_valid: bool
⋮----
reasons: list[str] = []
⋮----
audit_path = Path(audit_path)
⋮----
json_report = verify_jsonl_audit(audit_path)
chain_report = verify_audit_chain(audit_path)
audit_valid = json_report.valid and chain_report.valid
⋮----
audit_valid = True
⋮----
state_files_valid = True
⋮----
path = Path(item)
⋮----
state_files_valid = False
⋮----
jsonl_files_valid = True
⋮----
jsonl_files_valid = False
⋮----
chain = readiness_history_store.verify_chain()
⋮----
active_artifact_valid = True
⋮----
active = champion_registry.active()
⋮----
promotions = [
⋮----
event = promotions[-1]
⋮----
active_artifact_valid = False
⋮----
artifact = Path(event.artifact_path)
⋮----
snapshot_available = snapshot_store.latest_valid() is not None
ready = (
```

## File: ai_trading/state_hash.py
```python
def canonical_state_hash(value: Any) -> str
⋮----
value = asdict(value)
canonical = json.dumps(
⋮----
def file_state_hash(path: str | Path) -> str
⋮----
path = Path(path)
⋮----
payload = json.loads(path.read_text(encoding="utf-8"))
```

## File: ai_trading/state_snapshot.py
```python
@dataclass(frozen=True)
class SnapshotManifest
⋮----
created_at_utc: str
files: dict[str, str]
source_paths: dict[str, str]
⋮----
class AtomicSnapshotStore
⋮----
@staticmethod
    def _sha256(path: Path) -> str
⋮----
digest = hashlib.sha256()
⋮----
def create(self, files: list[str | Path]) -> Path
⋮----
stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
final_dir = self.root / stamp
temp_dir = self.root / f".{stamp}.tmp"
⋮----
manifest: dict[str, str] = {}
source_paths: dict[str, str] = {}
used_names: set[str] = set()
⋮----
source = Path(item)
⋮----
name = source.name
⋮----
prefix = hashlib.sha256(str(source).encode("utf-8")).hexdigest()[:12]
name = f"{prefix}-{source.name}"
⋮----
destination = temp_dir / name
⋮----
payload = SnapshotManifest(
⋮----
def valid_snapshots(self) -> list[Path]
⋮----
valid_snapshots: list[Path] = []
⋮----
manifest_path = directory / "manifest.json"
⋮----
payload = json.loads(manifest_path.read_text(encoding="utf-8"))
⋮----
files = payload.get("files", {})
valid = True
⋮----
path = directory / name
⋮----
valid = False
⋮----
def latest_valid(self) -> Path | None
⋮----
snapshots = self.valid_snapshots()
⋮----
def prune(self, keep_last: int = 20) -> int
⋮----
snapshots = sorted(
removed = 0
⋮----
snapshot = Path(snapshot)
⋮----
destination_root = Path(destination_root)
⋮----
manifest = json.loads((snapshot / "manifest.json").read_text(encoding="utf-8"))
source_paths = manifest.get("source_paths", {})
⋮----
source = snapshot / name
original = source_paths.get(name)
destination = Path(original) if original else destination_root / name
⋮----
temp = destination.with_suffix(destination.suffix + ".restore.tmp")
⋮----
def restore_latest(self, destination_root: str | Path = "artifacts") -> Path
⋮----
snapshot = self.latest_valid()
```

## File: ai_trading/stress_engine.py
```python
@dataclass(frozen=True)
class StressScenario
⋮----
name: str
volatility_multiplier: float = 1.0
correlation_multiplier: float = 1.0
gap_shock: float = 0.0
slippage_bps: float = 0.0
liquidity_scale: float = 1.0
⋮----
@dataclass(frozen=True)
class StressPolicy
⋮----
max_loss: float = 0.08
max_stressed_cvar: float = 0.06
monte_carlo_paths: int = 2000
horizon_days: int = 5
random_state: int = 42
⋮----
@dataclass(frozen=True)
class StressReport
⋮----
worst_loss: float
stressed_cvar: float
risk_scale: float
approved: bool
worst_scenario: str
scenario_losses: dict[str, float]
⋮----
DEFAULT_SCENARIOS = (
⋮----
clean = returns.astype(float).dropna()
cov = clean.cov().to_numpy(dtype=float)
std = np.sqrt(np.clip(np.diag(cov), 0.0, None))
corr = clean.corr().fillna(0.0).to_numpy(dtype=float)
stressed_corr = np.eye(len(std)) + (corr - np.eye(len(std))) * scenario.correlation_multiplier
stressed_corr = np.clip(stressed_corr, -0.99, 0.99)
⋮----
stressed_std = std * scenario.volatility_multiplier
⋮----
policy = policy or StressPolicy()
aligned = returns.loc[:, weights.index].dropna()
⋮----
w = weights.astype(float).to_numpy(dtype=float)
mean = aligned.mean().to_numpy(dtype=float)
rng = np.random.default_rng(policy.random_state)
⋮----
scenario_losses: dict[str, float] = {}
all_losses: list[float] = []
⋮----
cov = _stressed_covariance(aligned, scenario)
sims = rng.multivariate_normal(
portfolio = np.einsum("phn,n->ph", sims, w)
compounded = np.prod(1.0 + portfolio, axis=1) - 1.0
⋮----
losses = -compounded
⋮----
loss_series = pd.Series(all_losses, dtype=float)
cutoff = float(loss_series.quantile(0.95))
stressed_cvar = float(loss_series[loss_series >= cutoff].mean())
worst_scenario = max(scenario_losses, key=scenario_losses.get)
worst_loss = float(scenario_losses[worst_scenario])
⋮----
scale_candidates = [1.0]
⋮----
risk_scale = float(np.clip(min(scale_candidates), 0.0, 1.0))
⋮----
approved = worst_loss <= policy.max_loss and stressed_cvar <= policy.max_stressed_cvar
```

## File: ai_trading/supervisor_lease.py
```python
@dataclass(frozen=True)
class SupervisorLease
⋮----
owner_pid: int
acquired_at_utc: str
token: str
⋮----
class SupervisorLeaseStore
⋮----
def __init__(self, path: str | Path = "artifacts/supervisor_lease.json") -> None
⋮----
def load(self) -> SupervisorLease | None
⋮----
@staticmethod
    def pid_alive(pid: int) -> bool
⋮----
def acquire(self, token: str) -> SupervisorLease
⋮----
current = self.load()
⋮----
lease = SupervisorLease(
⋮----
temp = self.path.with_suffix(".tmp")
⋮----
def release(self, token: str) -> None
```

## File: ai_trading/supervisor_state.py
```python
@dataclass(frozen=True)
class SupervisorState
⋮----
status: str = "stopped"
worker_pid: int | None = None
restarts: int = 0
last_transition_utc: str = ""
reason: str = ""
⋮----
class SupervisorStateStore
⋮----
def __init__(self, path: str | Path = "artifacts/supervisor_state.json") -> None
⋮----
def load(self) -> SupervisorState
⋮----
state = SupervisorState(
⋮----
temp = self.path.with_suffix(".tmp")
```

## File: ai_trading/supervisor.py
```python
@dataclass(frozen=True)
class SupervisorConfig
⋮----
max_restarts: int = 10
crash_window_seconds: float = 60.0
max_crashes_in_window: int = 3
initial_backoff_seconds: float = 2.0
max_backoff_seconds: float = 60.0
worker_timeout_seconds: float | None = None
heartbeat_timeout_seconds: float = 180.0
heartbeat_startup_grace_seconds: float = 30.0
readiness_timeout_seconds: float = 30.0
require_qualification: bool = False
qualification_symbols: tuple[str, ...] = ()
qualification_period: str = ""
qualification_interval: str = ""
qualification_max_age_hours: float = 24.0
require_reliability_qualification: bool = False
min_reliability_score: float = 90.0
min_normal_ratio: float = 0.90
max_halt_ratio: float = 0.01
max_mttr_seconds: float | None = None
min_reliability_observation_seconds: float = 86_400.0
⋮----
@dataclass(frozen=True)
class SupervisorResult
⋮----
restarts: int
stopped_for_maintenance: bool
crash_loop_detected: bool
final_exit_code: int | None
⋮----
class PaperSupervisor
⋮----
def _halt_governor(self, reason: str) -> None
⋮----
previous = self.governor_store.load()
⋮----
def run(self) -> SupervisorResult
⋮----
token = secrets.token_hex(16)
⋮----
crashes: list[float] = []
restarts = 0
final_exit: int | None = None
⋮----
startup = run_startup_check(
⋮----
reliability = (
guard = validate_qualification_record(
⋮----
reason = "paper qualification gate failed: " + "; ".join(
⋮----
resilience = self.resilience_store.load()
⋮----
maintenance = self.maintenance_store.load()
⋮----
process = subprocess.Popen(self.command)
⋮----
readiness = wait_for_worker_readiness(
⋮----
watch_reason = readiness.reason
final_exit = process.returncode
runtime = readiness.waited_seconds
⋮----
watch = monitor_worker(
watch_reason = watch.reason
final_exit = watch.exit_code
runtime = watch.runtime_seconds
⋮----
now = time.monotonic()
crashes = [
⋮----
delay = min(
```

## File: ai_trading/temporal_cv.py
```python
@dataclass(frozen=True)
class FoldResult
⋮----
metrics: PerformanceMetrics
accuracy: float
observations: int
⋮----
@dataclass(frozen=True)
class TemporalCVReport
⋮----
folds: tuple[FoldResult, ...]
mean_accuracy: float
mean_sharpe: float
worst_drawdown: float
aggregate_score: float
⋮----
features = make_features(df)
labels = make_labels(
usable = features.dropna().index.intersection(labels.dropna().index)
⋮----
split_folds = purged_expanding_folds(
⋮----
results: list[FoldResult] = []
⋮----
train_idx = split.train_index
test_idx = split.test_index
⋮----
model = SpecialistDirectionModel(kind, random_state=42 + fold_number)
⋮----
equity = [100_000.0]
correct = 0
observations = 0
⋮----
pred = model.predict_one(features.loc[idx])
label = int(labels.loc[idx])
⋮----
pos = int(df.index.get_loc(idx))
⋮----
next_idx = df.index[pos + 1]
ret = float(df.at[next_idx, "Close"] / df.at[next_idx, "Open"] - 1.0)
⋮----
metrics = compute_metrics(pd.Series(equity, dtype=float))
⋮----
mean_accuracy = sum(r.accuracy for r in results) / len(results)
mean_sharpe = sum(r.metrics.sharpe for r in results) / len(results)
worst_drawdown = max(r.metrics.max_drawdown for r in results)
aggregate_score = (
```

## File: ai_trading/trade_journal.py
```python
@dataclass(frozen=True)
class TradeSnapshot
⋮----
timestamp_utc: str
symbol: str
side: str
quantity: float
price: float
status: str
pnl: float = 0.0
pnl_known: bool | None = None
confidence: float | None = None
strategy: str = ""
⋮----
def __post_init__(self) -> None
⋮----
class TradeJournal
⋮----
"""Append-only JSONL journal used as the dashboard's stable event boundary."""
⋮----
def __init__(self, path: str | Path = "artifacts/trades.jsonl") -> None
⋮----
def append(self, trade: TradeSnapshot) -> None
⋮----
def list(self, *, limit: int | None = None) -> tuple[TradeSnapshot, ...]
⋮----
rows: list[TradeSnapshot] = []
⋮----
rows = rows[-limit:]
```

## File: ai_trading/tuning.py
```python
@dataclass(frozen=True)
class OptimizationWeights
⋮----
return_weight: float = 1.0
sharpe_weight: float = 0.35
sortino_weight: float = 0.15
drawdown_penalty: float = 1.25
⋮----
@dataclass(frozen=True)
class TuningResult
⋮----
best_score: float
best_params: dict[str, float]
trials: int
⋮----
"""Risk-aware scalar objective for hyperparameter searches."""
weights = weights or OptimizationWeights()
⋮----
sampler = optuna.samplers.TPESampler(seed=random_state)
study = optuna.create_study(direction="maximize", sampler=sampler)
⋮----
def objective(trial: optuna.Trial) -> float
⋮----
risk = RiskConfig(
model = ModelConfig(
wf = WalkForwardConfig(
report = WalkForwardBacktester(
```

## File: ai_trading/watchdog_enforcer.py
```python
@dataclass(frozen=True)
class WatchdogEnforcement
⋮----
healthy: bool
halted: bool
reasons: tuple[str, ...]
⋮----
reasons: list[str] = []
heartbeat = heartbeat_store.load()
⋮----
audit_path = Path(audit_path)
⋮----
json_report = verify_jsonl_audit(audit_path)
chain_report = verify_audit_chain(audit_path)
⋮----
previous = governor_store.load()
```

## File: ai_trading/watchdog.py
```python
@dataclass(frozen=True)
class Heartbeat
⋮----
component: str
timestamp_utc: str
iteration: int
status: str
⋮----
@dataclass(frozen=True)
class WatchdogPolicy
⋮----
max_heartbeat_age_seconds: float = 180.0
⋮----
class HeartbeatStore
⋮----
def __init__(self, path: str | Path = "artifacts/heartbeat.json") -> None
⋮----
def write(self, component: str, iteration: int, status: str = "ok") -> Heartbeat
⋮----
hb = Heartbeat(
⋮----
temp = self.path.with_suffix(".tmp")
⋮----
def load(self) -> Heartbeat | None
⋮----
def heartbeat_age_seconds(heartbeat: Heartbeat, *, now: datetime | None = None) -> float
⋮----
now = now or datetime.now(UTC)
timestamp = datetime.fromisoformat(heartbeat.timestamp_utc)
⋮----
policy = policy or WatchdogPolicy()
```

## File: ai_trading/worker_monitor.py
```python
@dataclass(frozen=True)
class WorkerMonitorConfig
⋮----
poll_seconds: float = 1.0
startup_grace_seconds: float = 30.0
max_runtime_seconds: float | None = None
heartbeat_max_age_seconds: float = 180.0
⋮----
@dataclass(frozen=True)
class WorkerMonitorResult
⋮----
exit_code: int | None
runtime_seconds: float
reason: str
forced_stop: bool
⋮----
config = config or WorkerMonitorConfig()
started = time.monotonic()
⋮----
exit_code = process.poll()
runtime = time.monotonic() - started
⋮----
reason = "worker runtime timeout"
⋮----
heartbeat = heartbeat_store.load()
⋮----
reason = "worker heartbeat stale"
```

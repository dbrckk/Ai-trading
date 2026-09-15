# Ai-trading

Autonomous trading research platform focused on reproducible, risk-aware, out-of-sample evaluation.

## Current capabilities

- OHLCV ingestion through `yfinance`
- deterministic feature engineering
- LONG / SHORT / FLAT probabilistic model
- independent fail-closed risk engine
- configurable transaction costs and slippage
- paper broker
- purged walk-forward validation
- next-bar-open execution in walk-forward tests
- buy-and-hold benchmark
- Sharpe, Sortino, Calmar, annualized return/volatility and max drawdown
- append-only experiment registry
- durable PostgreSQL persistence for hosted paper runtime state
- CI with Ruff + Pytest + PostgreSQL 16 integration tests

The optimization target is **risk-adjusted net performance after costs**, not raw backtest profit or win rate.

## Architecture

```text
Market data
    |
    v
Feature engine
    |
    v
Model / ensemble
    |
    v
Signal
    |
    v
Independent risk engine
    |
    +---- reject
    |
    v
Paper / execution adapter
    |
    v
Equity + audit trail
    |
    v
Walk-forward evaluation
    |
    v
Experiment registry
```

## Quick start

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

ai-trading train --symbol GC=F --period 5y
ai-trading paper --symbol GC=F --period 5y
ai-trading walk-forward --symbol GC=F --period 10y

pytest
```

Windows PowerShell:

```powershell
.venv\Scripts\Activate.ps1
```

## Validation path

Run the local validation stack before using real market data:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

ruff check src tests
pytest -q
pytest -q tests/test_smoke_e2e.py
```

Then exercise the real-data paper path:

```bash
ai-trading train --symbol GC=F --period 5y
ai-trading walk-forward --symbol GC=F --period 10y
ai-trading multiasset-step --symbols GC=F,SI=F,CL=F --period 2y
ai-trading readiness-check --symbol GC=F --period 10y
ai-trading system-status
```

The project remains paper-only. A live broker adapter is intentionally not enabled.

For release-readiness validation, set a signing key outside the repository:

```bash
export AI_TRADING_RELEASE_SIGNING_KEY="replace-with-a-private-secret"
ai-trading create-readiness-release
ai-trading deployment-readiness
```

A readiness release can be invalidated explicitly:

```bash
ai-trading revoke-readiness-release --reason "superseded or invalidated"
```

## Durable hosted paper persistence

Local development uses the existing `artifacts/` files by default. A hosted deployment can make PostgreSQL authoritative by setting:

```text
AI_TRADING_DATABASE_URL=<PostgreSQL connection string with TLS enabled>
```

When this variable is present, the paper runtime stores its portfolio state, River online model, trade history, append-only audit chain, revision counter, and hosted worker status in PostgreSQL. The dashboard and hosted worker share the same persistence backend and runtime key, so state can be restored after a process restart or service sleep.

The PostgreSQL path is intentionally fail-closed. If `AI_TRADING_DATABASE_URL` is present but invalid, unavailable, or cannot initialize its schema, the service does **not** silently fall back to local files. If the variable is absent, the application keeps the backward-compatible local file mode.

Treat the database connection string as a secret. Do not commit it, print it, expose it through the dashboard, or include it in exception payloads. Production deployments should use a TLS-enabled provider connection string.

Persistence commits use revision-based overlap protection and one database transaction for state, online model, optional paper trade, and audit event. A conflicting worker receives a persistence conflict instead of overwriting a newer revision.

This persistence layer does not enable live trading. Broker routing remains paper-only.

## Walk-forward methodology

The V1 evaluator uses sequential out-of-sample folds.

For every fold:

1. only observations strictly before the test window are used for training;
2. the end of the training set is purged by the prediction horizon;
3. the model is fitted again on historical data only;
4. a signal is computed from bar *t*;
5. the simulated order is executed at bar *t+1* open;
6. transaction costs and slippage are deducted;
7. risk limits are applied independently from the predictive model;
8. strategy equity is compared with buy-and-hold on the same out-of-sample period.

This design reduces look-ahead leakage and makes reported performance harder to overstate.

## Experiments

By default:

```bash
ai-trading walk-forward --symbol GC=F --period 10y
```

appends a JSON record to:

```text
artifacts/experiments.jsonl
```

The registry stores the model/risk/walk-forward configuration, strategy metrics, benchmark metrics, fold count, decision count and trade count.

## star-list integration strategy

The companion `star-list` catalog identifies the components we intend to integrate progressively rather than importing a large dependency stack immediately.

High-priority candidates:

- **QuantConnect/Lean** — mature backtesting/execution
- **NautilusTrader** — event-driven execution realism
- **vectorbt** — fast research and parameter sweeps
- **Microsoft Qlib** — quantitative ML research
- **River** — online learning
- **XGBoost / CatBoost** — tabular alpha models
- **Optuna** — constrained hyperparameter optimization
- **hmmlearn / statsmodels / arch** — regimes and volatility
- **Riskfolio-Lib / skfolio** — portfolio/risk optimization
- **QuantStats** — reporting
- **OpenBB** — financial and macro data

## Safety defaults

Live order routing is not included yet. The repository currently executes only simulated orders.

The predictive model cannot bypass the risk engine. A future live adapter must remain downstream of the same risk checks and must include explicit activation, exposure caps, kill switches and auditable order state.

## Roadmap

- [x] V0 — data, features, baseline ML model, paper broker, risk engine
- [x] V1 — purged walk-forward evaluation, realistic next-bar execution, metrics, benchmark, experiment registry
- [x] V2 — regime detection + model ensemble + constrained optimization foundations
- [x] V3 — bootstrap robustness + champion/challenger promotion
- [ ] V4 — external live execution adapter (NautilusTrader or Lean)
- [x] V5 — multi-asset portfolio allocation and portfolio-level risk
- [x] V6 — guarded continuous learning, drift detection, rollback and resilience governance

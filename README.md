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
- CI with Ruff + Pytest

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
- [ ] V2 — regime detection + model ensemble + constrained Optuna search
- [ ] V3 — Monte Carlo / bootstrap robustness + champion/challenger promotion
- [ ] V4 — event-driven execution adapter (NautilusTrader or Lean)
- [ ] V5 — multi-asset portfolio allocation and portfolio-level risk
- [ ] V6 — guarded continuous learning with drift detection and automatic rollback

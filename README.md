# Ai-trading

Autonomous trading research platform focused on reproducible, risk-aware, out-of-sample evaluation.

## Current capabilities

- hardened OHLCV ingestion through `yfinance` with retries, sorting, timestamp deduplication and fail-closed OHLC validation
- deterministic feature engineering
- paper-direction model with explicit risk checks (legacy River-v1 is binary; a three-class River challenger is evaluated offline)
- independent fail-closed risk engine
- configurable transaction costs and slippage
- paper broker
- purged walk-forward validation
- next-bar-open execution in walk-forward tests
- buy-and-hold benchmark
- Sharpe, Sortino, Calmar, annualized return/volatility and max drawdown
- append-only experiment registry
- durable PostgreSQL persistence for hosted paper runtime state
- Gold / DAX / BTC multi-market paper runtime with session-aware freshness telemetry
- multi-timeframe evidence across 5m / 15m / 1h / 4h
- correlation-aware portfolio de-risking and fail-closed configuration validation
- bounded external paper-cycle scheduling with catch-up support
- Cloudflare fifteen-minute scheduler with authenticated Render endpoint and durable delivery evidence
- GitHub Actions hourly authenticated fallback (reuses Render/Neon, skips recent Cloudflare success to conserve free compute; 45-second maximum status probe and 180-second authenticated cycle timeout accommodate Render cold starts)
- read-only hosted dashboard backed by the same durable runtime state
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

## Numeric fail-closed controls

Paper trading and research reject non-finite capital, cost/slippage and label
threshold configuration. Before any paper risk approval, portfolio equity,
risk baselines, held notional, model direction and confidence must be valid.
Corrupt runtime inputs block new exposure without issuing an untrusted forced
exit. Valid hard loss stops continue to liquidate existing paper exposure.
The global risk governor also halts on non-finite model-confidence, data-quality,
stress-loss or drawdown evidence. Portfolio exposure analysis rejects invalid
capital, notionals and non-finite configured risk limits instead of reporting
approval based on NaN comparisons.
These protections do not activate a live broker or improve proven profitability.

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

### Continuous paper production mode

The production paper architecture separates execution from the hosted web process:

```text
Cloudflare Worker (every 15 minutes)
        |
        | authenticated POST
        v
Render /internal/paper-cycle
        |
        v
Shared PostgreSQL durable state
        |
        +---------------------------+
        |                           |
        v                           v
paper state/model/trades         Render dashboard
        ^
        |
GitHub Actions fallback scheduler
```

The primary scheduler is the Cloudflare Worker under `infra/cloudflare-paper-scheduler/`. Its cron runs every fifteen minutes and sends an authenticated POST to Render's `/internal/paper-cycle` endpoint. The Worker contains no database credentials and no trading logic. The hourly `.github/workflows/paper-cycle.yml` fallback calls the same authenticated Render endpoint, skipping the POST when Cloudflare succeeded within the last 32 minutes (matching the dashboard's health window). Render alone holds the database connection; GitHub Actions does not store it. Both schedulers process Gold (`GC=F`), DAX (`^GDAXI`) and BTC (`BTC-USD`) independently, so one market failure does not prevent the others from advancing. GitHub scheduled jobs can be delayed; this fallback does not guarantee an exact heartbeat.

The hosted runtime heartbeat uses the **15-minute external scheduler cadence**, not the **5-minute candle interval**. It reports a stale engine after roughly three missed scheduler periods (45 minutes); the dashboard's individual paper signal is independently withheld once its underlying 5-minute bar decision is older than 15 minutes, or if the market session is closed. This avoids falsely marking a healthy scheduler stale without treating an older signal as current.

**Deployment provenance.** Render provides `RENDER_GIT_COMMIT` automatically.
The read-only `/livez` endpoint includes `deployed_commit` when a valid
40-character SHA is available. Use the manual **Hosted Dashboard Probe**
GitHub Actions workflow with its optional `expected_sha` input. Alternatively,
set `RENDER_RELEASE_SHA` to the intended 40-character deployed commit, then run:

```bash
python -m ai_trading.deployment_probe \
  --base-url https://ai-trading-dashboard-qyr2.onrender.com \
  --expected-sha "$RENDER_RELEASE_SHA"
```

A missing or mismatched deployed SHA fails that explicit check even when
`/readyz` succeeds. Scheduled and automatic probes continue to check
liveness, storage, and all three markets without requiring a particular SHA,
because Render deploys asynchronously and `[skip render]` metadata-only
commits can advance `main` without a new release. Compare against the
intended **deployed release**, not blindly against the newest `main` commit.

Scheduler delivery telemetry is sanitized and persisted durably. The application never persists the bearer token or raw authorization headers. A partially failed multi-market cycle returns **HTTP 503**, and the Cloudflare Worker also checks the JSON `ok` flag on successful HTTP responses. Failures are observable rather than falsely reported as successful; Render logs contain only known failed market symbols and sanitized failure codes, not provider exception text. Three consecutive successful Cloudflare deliveries are treated as the minimum verification threshold exposed by `/api/scheduler`.

The production cycle is:

```bash
ai-trading paper-cycle --symbol GC=F --period 5d --interval 5m --max-catchup-bars 72
```

Its durable runtime key is:

```text
paper:GC=F:5m:online-river:v1
```

A fresh durable runtime processes only the latest eligible execution bar. An existing runtime catches up missed eligible bars oldest-first, with at most 72 attempted bars per invocation (six hours of 5-minute bars) so delayed external triggers can recover without unbounded work. If the durable `last_processed` marker is outside the loaded history window, the cycle fails closed instead of guessing where to resume. Revision conflicts cause state to be reloaded so overlapping executors cannot overwrite newer durable progress.

Per-market paper execution costs can be overridden without changing code by setting `AI_TRADING_EXECUTION_COSTS_JSON`. When unset, the existing global `RiskConfig` transaction-cost and slippage defaults are preserved exactly. Overrides are exact-symbol matches and malformed or negative values fail closed.

```json
{
  "GC=F": {"transaction_cost_bps": 2.0, "slippage_bps": 1.0},
  "BTC-USD": {"transaction_cost_bps": 3.0, "slippage_bps": 2.0}
}
```

The example only demonstrates the configuration format; production values should be calibrated from observed execution/spread data rather than assumed from the example.

### Interpreting paper signals

`/api/markets` and the dashboard show the **last completed paper decision**, not a
live order recommendation. The Cloudflare/Render scheduler must process a new bar
before a new signal becomes available. The per-market API exposes:

- `signal`, `confidence`: the actual River prediction, only when it is recent
  and based on a completed paper step (not the default FLAT/0% fallback).
- `risk_approved`, `decision_reason`: the independent risk engine's decision,
  not an assessment of future profitability.
- `signal_state`: `PAPER_APPROVED`, `RISK_REJECTED`, `NO_TRADE`, `WAITING`,
  `DELAYED`, `UNVERIFIED` or `UNAVAILABLE`. Only a fresh, verified,
  in-session decision may expose a side and confidence.
- `signal_time`, `signal_age_seconds`: evidence of when the paper decision
  was processed. A stale, unparseable or timezone-naive timestamp suppresses
  signal publication. For a 5-minute market, decisions expire after 15 minutes.
  A successful poll with **no new eligible bar** preserves the previous
  completed paper decision only if the stored bar and revision agree; it
  **does not** refresh the signal timestamp or represent a new trade.
- `freshness` and `heartbeat_age_seconds`: separate scheduler/data health.
  A healthy heartbeat **alone** never makes an old prediction tradable.

**Model limitation:** the persisted River-v1 direction classifier uses a
binary logistic regression despite carrying `-1 / 0 / +1` labels. Its
current probability map cannot assign a nonzero probability to SHORT.
Do not interpret this as validated bearish-market coverage. A
**research-only** three-class River alternative is evaluated against
the actual pretrained Kronos model and momentum in
[the offline study](docs/kronos-research.md), using identical
future-matured labels, next-bar entry, exit horizon and costs. Neither
alternative is automatically promoted into the existing persisted
production model or trading decisions.

All trades are simulated. These fields do not include live quotes, broker fills,
spread guarantees, stop loss or actionable entries; do not manually copy the
historical paper decisions into live orders. Kronos remains an independent,
unvalidated research challenger.

### Hosted dashboard

The read-only production paper dashboard is available at:

```text
https://ai-trading-dashboard-qyr2.onrender.com
```

Operational endpoints:

```text
https://ai-trading-dashboard-qyr2.onrender.com/api/overview
https://ai-trading-dashboard-qyr2.onrender.com/api/markets
https://ai-trading-dashboard-qyr2.onrender.com/api/scheduler
https://ai-trading-dashboard-qyr2.onrender.com/api/status
https://ai-trading-dashboard-qyr2.onrender.com/livez
https://ai-trading-dashboard-qyr2.onrender.com/readyz
https://ai-trading-dashboard-qyr2.onrender.com/healthz
```

The Render web service should use the same `AI_TRADING_DATABASE_URL` and run with:

```text
AI_TRADING_HOSTED_PAPER=1
AI_TRADING_EXTERNAL_SCHEDULER=1
AI_TRADING_HOSTED_SYMBOL=GC=F
AI_TRADING_HOSTED_PERIOD=5d
AI_TRADING_HOSTED_INTERVAL=5m
```

The Render Blueprint (`render.yaml`) declares these paper-only variables and
requests `AI_TRADING_DATABASE_URL` and `AI_TRADING_SCHEDULER_TOKEN` using
`sync: false`. Set the database URL to the shared durable PostgreSQL/Neon database used
by Render's web and paper-cycle endpoint; the GitHub fallback no longer
requires a database URL. Provide the same scheduler token used by Cloudflare. Neither
secret belongs in Git or in HTTP endpoints. Existing Render services must
also have these values configured; changing the Blueprint does not prove
the hosted service was successfully deployed.

`AI_TRADING_EXTERNAL_SCHEDULER=1` explicitly suppresses the legacy in-process daemon worker. Render serves the dashboard and the authenticated cycle endpoint while external schedulers own delivery. The dashboard reads the shared durable state and exposes the last processed bar, processed-bar count, per-market freshness and durable scheduler evidence without exposing storage connection details.

The scheduler verification endpoint reports recent sanitized deliveries, the current consecutive Cloudflare-success count and whether the three-delivery verification threshold has been reached. A successful HTTP trigger with zero newly processed bars is still a valid delivery: duplicate/overlapping invocations are intentionally benign and durable runtime revision protection prevents stale writers from overwriting newer state.

Health probes intentionally have separate semantics: `/livez` checks only that the HTTP process is alive, `/readyz` returns HTTP 503 when durable storage is unavailable **or** the external scheduler is enabled without its required token/durable database, and `/healthz` remains the backwards-compatible detailed runtime health view. Market/provider errors therefore do not masquerade as web-process failures.

`.github/workflows/hosted-dashboard-probe.yml` runs a read-only external
probe every two hours (plus pushes touching the hosted configuration). It
separately checks `/livez`, `/readyz`, and that `/api/markets` contains
Gold, DAX and BTC **with complete portfolio data, no market storage errors,
and all three engines RUNNING with zero consecutive cycle errors**.
This stricter scheduled probe prevents a misleading green result when engines
remain stuck in `STARTING` or turn `STALE`; a routine dashboard-only
inspection can omit `--require-running-markets`.
Known readiness HTTP 503 responses distinguish `configuration_incomplete`
from `storage_unavailable` without publishing exception text or secrets.
It reports a failing GitHub Actions job if the
publicly hosted service is unavailable or incomplete. This check **does
not** invoke the scheduler, place trades, wake workers, or guarantee
fresh market data. For manual diagnosis, use
`PYTHONPATH=src python -m ai_trading.deployment_probe --base-url https://ai-trading-dashboard-qyr2.onrender.com --require-running-markets`.

## Hosted probe transient connection recovery

The read-only hosted dashboard check makes **one bounded (10-second) retry**
for an endpoint only if its first request had a transport connection failure,
and only after checking the other endpoints. This handles the observed
Render `/livez` transient failure followed by healthy `/readyz` and
Gold/DAX/BTC readings. Persistent connection failures, HTTP errors,
unhealthy services, non-running market engines and deployment SHA mismatches
remain failures; the probe never places or schedules trades.

## Positive out-of-sample profitability is required

The read-only walk-forward benchmark gate now fails closed when net
out-of-sample total return is **zero or negative**, even when the strategy
beats a more strongly declining buy-and-hold benchmark. Non-finite
performance statistics also fail the benchmark gate rather than silently
passing comparisons. This is additional research validation alongside the
existing Sharpe, Sortino, Calmar, drawdown, fold and trade-count thresholds,
not an automatic model promotion or permission to trade live.

## Bootstrap research evidence validation

The bootstrap robustness gate fails closed on fewer than 100 simulations,
non-finite statistics, impossible outcome probabilities, or incoherent
return and drawdown quantiles. NaN comparisons must never pass research
qualification. This check neither enables live trading nor proves an
investment edge.

## Parameter sensitivity requires actual net-profit evidence

The read-only parameter-sensitivity research gate rejects scenarios with
**non-positive net total return**, zero executed trades, non-finite
performance metrics or negative drawdown values. A strategy that merely
outperforms a declining benchmark cannot pass based on relative excess
return alone. The existing minimum scenario pass ratio, Sharpe and
drawdown constraints remain in effect; this is not a model promotion or
permission to trade live.

## Profit resilience under execution costs

The cost-stress gate now requires the **highest transaction-cost-plus-slippage
scenario** to retain positive net return, in addition to the existing
minimum pass ratio, Sharpe and drawdown checks. This prevents a favorable
majority of cheap scenarios from concealing losses when execution becomes
expensive. The strict requirement is on by default and can be explicitly
disabled in `CostStressGatePolicy` for research comparisons; it does not
enable live execution or prove future profitability.

## Paper trade performance evidence

The read-only performance API exposes `evidence_sufficient` separately from
`available`: at least **30 paper fill events with known realized PnL** and at least
**95% PnL coverage** are required before even treating headline paper PnL,
profit factor or drawdown as a minimally populated sample. These are **fill
events, not 30 independent completed trades**, so no statistical conclusion
follows from satisfying them. These thresholds
are a descriptive sample-coverage check, **not statistical proof of edge**.
The payload also reports `minimum_pnl_observations` and
`minimum_pnl_coverage`. Actual execution costs must be accounted for in
paper fills; further independent out-of-sample, regime, uncertainty and
net-of-cost checks remain mandatory. No automated model promotion, paper
order decision or live broker permission depends on this flag.

The dashboard now shows **net realized paper PnL** alongside portfolio
mark-to-market PnL and per-market allocation-adjusted realized PnL, plus
observed PnL fill coverage and `PRELIMINARY` / `DATA MINIMUM` sample
labels. `DATA MINIMUM` means coverage thresholds were met, **not** that
the strategy is profitable. These are read-only reporting fields.

### Net-of-cost research qualification

Walk-forward cost stress uses the paper broker's transaction costs and
slippage for each scenario. The research-only `CostStressGate` now rejects
scenarios with **non-positive absolute net return**, invalid/non-finite
performance metrics or no executions, even when a strategy loses less than
a falling buy-and-hold benchmark. Its existing drawdown, Sharpe and excess
return limits also remain enforced. This gate is not connected to live or
paper order approval; a positive backtest is not proof of future profits.

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
## Regime robustness validation

Market-regime research rejects NaN and infinite regime returns before
ranking worst regimes or checking return dispersion. Invalid results must
not qualify a strategy. This is a research-only diagnostic; no broker,
execution or risk-sizing configuration is changed.


## Execution-cost attribution research

The read-only `turnover-study` comparison additionally reruns the **baseline
(0% turnover deadband)** with the same chronological walk-forward configuration
but zero modeled transaction costs and slippage. Its JSON
`baseline_cost_sensitivity` section reports zero-cost validation/holdout/full
returns, the corresponding differences versus the fee-inclusive baseline,
and whether the strategy was positive only in this hypothetical zero-cost
setting. The difference is **not** an exact fee ledger: altered portfolio
equity can affect subsequent position sizing and risk decisions.

This diagnostic distinguishes an execution-friction sensitivity problem from
an already-unprofitable zero-cost proxy. It does not validate the hosted
River-v1 model, authorize parameter changes, or guarantee profits.

## Experimental turnover control (paper trading only)

Excessive small same-direction rebalances can consume paper PnL through
transaction costs and slippage. The broker and walk-forward backtester now
share an optional `RiskConfig.min_rebalance_fraction` setting (default
**0.0 / disabled**). When explicitly enabled, a proposed same-direction
notional adjustment smaller than this fraction of current equity is skipped
and incurs no simulated trading costs. Opening from flat, changing direction,
and exiting to flat (including loss-limit forced exits) are never skipped.

The per-market JSON override can set e.g.
`AI_TRADING_EXECUTION_COSTS_JSON='{"GC=F":{"min_rebalance_fraction":0.005}}'`.
This is **not enabled by default** and must first demonstrate improvement in
walk-forward net-of-cost performance across representative market conditions.
A deadband can reduce fees but may also delay beneficial risk adjustments;
there is no assurance it will improve PnL.

## Gold, DAX and BTC turnover comparison (research only)

Run a fee-inclusive, purged walk-forward comparison of the optional
same-direction rebalance deadband without touching hosted paper settings:

`python -m ai_trading.command_app turnover-study --symbols 'GC=F,^GDAXI,BTC-USD' --period 1mo --interval 5m --max-bars 1800 --output artifacts/turnover-study.json`

The report compares thresholds 0%, 0.10%, 0.25% and 0.50% of equity
using the same Yahoo Finance history, transaction costs and slippage
per market. It records the market-history SHA-256, sample window,
trade count, drawdown, and net returns for each threshold. A candidate
is chosen **only on earlier out-of-sample validation bars**; a later
out-of-sample holdout is reported separately. Insufficient evidence
(under 240 out-of-sample bars, 30 transactions or 4 folds), unprofitable
holdout returns, or excessive holdout drawdown prevents a positive
review result. The report remains review-only even if its holdout check
passes; this is not a statistically proven edge or an activation gate.

The analysis uses the offline `WalkForwardBacktester` prediction model,
**not the authoritative hosted River-v1 model**. Its results are only
proxy evidence, not a production profit forecast. Yahoo history can
change or fail to download; missing market data is explicitly reported,
never silently replaced by fabricated numbers. A manual GitHub Action
**Turnover Research** can run this comparison and retain a JSON
diagnostic artifact. No runtime, Cloudflare scheduler, live broker or
model-promotion setting is changed.

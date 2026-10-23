# Project state

Status: active

- **2026-10-23 backtest timeline integrity:** PR #205 is open (CI/CodeQL pending verification). Reject invalid/missing, duplicated or out-of-order timestamps and numeric indexes during period inference; also reject NaN/Inf walk-forward annualization overrides. This protects research metric credibility; it does not change production paper decisions, Kronos authority or enable real brokerage. Net-of-fees profitability remains unproven.

- **2026-10-21 cost-stress follow-up**: PR #183 was merged and current `main` CI/CodeQL are green after an initial PR test failure from stale exact-payload assertions. This branch strengthens the backtest cost-stress gate: highest combined transaction-cost/slippage scenario must have positive net return, even if most cheap scenarios pass. This is a conservative research gate, not a guarantee of profit or a live broker change.

## Working

- **2026-10-23 performance evidence integrity:** PR #202 and #203 merged with successful PR CI/CodeQL. This follow-up refuses incomplete/nonfinite/nonpositive walk-forward equity and benchmark inputs rather than silently removing missing rows and generating deceptive positive metrics. Performance scoring remains read-only research; live broker OFF, River-v1 paper authority, no automatic promotion.


- **2026-10-23 model qualification integrity:** PR #202 merged (unknown Gold/DAX/BTC held-pair correlation now fails closed, with green PR CI and CodeQL). Current branch rejects NaN/Inf/invalid metrics in standalone and multi-period challenger promotion, requires positive modeled challenger return, and rejects inconsistent or non-finite soak results and invalid policy thresholds. Research validation only; no production model change or live brokerage.


- **2026-10-23 global numerical risk evidence:** PR #200 merged after green CI and CodeQL, guarding paper RiskEngine and core configuration. An independent read-only turnover artifact (GitHub #12440979405) showed Gold baseline -0.253% after modeled fees vs +0.045% zero-cost, DAX -0.243% vs -0.063%, and BTC -0.687% vs -0.249% (offline proxy, not hosted River-v1; exact fee ledger not claimed). This branch rejects non-finite global governor telemetry and invalid portfolio exposure/capital/risk limits, with existing test coverage. Keep production market settings, River-v1 and live-broker OFF unchanged.


- **2026-10-23 core risk input safety:** Hosted Dashboard Probe run 39902075368 failed with all Gold/DAX/BTC in STARTING on first attempt; rerun passed web, readiness and three RUNNING motors at 06:24:56 UTC (exact Render deploy SHA not checked). PR #199 merged with successful CI/CodeQL; read-only fee/no-fee sensitivity is research only. New branch rejects non-finite RiskConfig cash/costs, ModelConfig return threshold and invalid paper portfolio/model forecasts before authorizing exposure; finite hard-loss stops still flatten. No change to default allocation or live-trading posture.


- **2026-10-22 fee attribution research:** strict hosted probe attempt 1 failed market engine health while web/storage were ready; attempt 2 at 14:51Z passed. PR #198 merged with CI/CodeQL green and safe per-market engine failure labels. Existing Gold/DAX/BTC 5m turnover study found net-negative proxy baseline across all markets and no robust positive holdout. New branch adds an offline zero-cost counterfactual baseline to distinguish cost sensitivity from weak zero-cost strategy returns; it does not change any paper trading behavior or auto-enable thresholds.

- **2026-10-22 hosted incident:** probe #39789764311 passed /livez and /readyz but failed strict Gold/DAX/BTC engine health; requested one diagnostic rerun to distinguish transient from persistent issue. This branch adds sanitized per-symbol status to future strict probe failure logs; it does not weaken health checks, touch scheduler/order execution, or change paper risk. The turnover study #197 found no profitable alternative and the default remains unchanged.



- **2026-10-22 confirmed research result:** GitHub run #39767234077 produced downloadable JSON artifact #12421490257 after correcting the command entrypoint. Each market: 1,800 5m candles; 1,516 OOS evaluations; 7 folds; costs 2bp plus 1bp slippage. Baseline net total return Gold -0.19833% (205 fills), DAX -0.24241% (238), BTC -0.36508% (273). Variants 0.1%/0.25%/0.5% of equity all remained net negative; selected validation threshold null for all three; holdout check false. Evidence covers short market windows and the offline proxy, not actual hosted River-v1 profitability. Keep the deadband OFF; do not infer profit improvement.

- **2026-10-22 Gold/DAX/BTC turnover evaluation:** new read-only comparison of four optional paper rebalance thresholds (0, 0.1%, 0.25%, 0.5% of equity), with fees and slippage, market-history SHA, early purged walk-forward validation and later holdout. Research uses offline proxy, not hosted River-v1; no automatic activation. The initial GitHub action returned false success without running command due to missing module entrypoint; fixed `command_app.__main__` and made missing artifact/command fatal; recheck workflow. PR #196 merged, post-merge main CI and CodeQL green.


- **2026-10-22 turnover research:** PR #195 merged after green CI and CodeQL. Added a disabled-by-default same-direction paper rebalance deadband to reduce simulated micro-order costs; preserved entries, flips and forced stop exits. The same broker is used by production paper runtime and walk-forward backtester, and per-market configuration can opt into the threshold. This remains unvalidated on actual multi-market paper returns; no live broker enabled.


- **2026-10-22**: PR #192 merged profitable/finite parameter sensitivity gate; duplicate #191 closed without merge, though its CI/CodeQL were green. PR #194 merged bootstrap validity checks. This branch rejects non-finite market regime returns before worst-regime ranking or dispersion calculation. No live trading changes.


- **2026-10-22 bootstrap research validation:** PR #192 already merged the positive-net-return parameter sensitivity safeguard; duplicate #191 closed. PR #193 merged bounded retries for transient hosted probe connections, with green hosted probe and CI. This branch requires bootstrap reports to contain finite, internally coherent probability and quantile evidence from at least 100 simulations; previous NaN/Inf values could silently evade comparisons. Research-only validation; live broker stays OFF.



- **2026-10-22 operational follow-up:** the latest GitHub Hosted Dashboard Probe run `39680748089` failed at `/livez: connection_failed`, but in the same run `/readyz: storage_ready` and `/api/markets: three_markets_running` passed. This does **not** establish a sustained Render outage. A bounded one-time read-only recheck of transport connection failures after the initial endpoint pass is being validated; persistent failures, bad HTTP/payload/engine and SHA mismatch still fail. PR #192 sensitivity net-return evidence gate merged with PR CI and CodeQL success; profit improvement remains unproven.


- **2026-10-22 sensitivity profit follow-up:** merged PR #188 already covered worst execution-cost losses; conflicting duplicate PR #190 was closed unmerged. This branch strengthens parameter sensitivity selection to require positive **absolute net** return, executed trades and finite performance per passing perturbation. Existing tests were extended in place; no new test modules, no changes to live broker, paper order routing or model promotion.


- **2026-10-21**: PR #188 merged with green CI/CodeQL; worst trading-cost scenario must have positive net return before cost-stress research gate passes. Current `fix/benchmark-positive-net-return` strengthens the separate walk-forward benchmark gate: reject negative/break-even net OOS returns even if relative return beats a declining index, and fail closed on NaN/Infinity. No live execution or automatic promotion.


- **2026-10-21 profit-preservation milestone:** PR #183 merged (30 known-PnL fill / 95% coverage *diagnostic*); PR #184 merged (existing long/short paper exposure forcibly flattened at next eligible bar after daily-loss/drawdown/insolvency hard stop, with fees and matching backtest, CI/CodeQL green); PR #185 merged (research cost-stress gate requires positive modeled **absolute net return**, finite metrics and at least one fill); PR #186 merged (Gold/DAX/BTC portfolio UI now distinguishes allocation-adjusted realized net PnL, mark-to-market PnL, and preliminary sample evidence, CI/CodeQL green).
- **2026-10-21 20:14 UTC strict GitHub hosted probe** run `39668531496` confirmed public `/livez`, `/readyz` and **three markets RUNNING**; it did **not** specify an expected SHA, so latest application release identity remains unverified. Real broker execution remains disabled, River-v2 shadow remains independently OFF by default. Minimal fill coverage is not profitability proof; next work must be net-of-cost out-of-sample evaluation, exact release validation, and bounded research.


- **2026-10-21:** PR #183 merged (`b966ed8`): API distinguishes populated paper performance from 30 known-PnL fill observations and 95% fill coverage. This is a **minimal data coverage check, not proof of a profitable strategy**.
- **2026-10-21:** PR #184 merged (`3c8f77e`): existing simulated long/short positions are exited at the next eligible bar after a hard drawdown, daily loss or depleted-equity stop; net fill costs are accounted for in runtime and walk-forward backtesting. Green PR CI/CodeQL. Future gaps/slippage mean a configured loss limit is not a guarantee of a capped realized loss.
- **Follow-up research:** `fix/research-cost-stress-positive-net-return` rejects non-positive absolute net returns and invalid/no-execution scenarios in the research cost-stress gate, in addition to relative benchmark/drawdown/Sharpe checks; no change to production trading decisions. Exact live Render deployed SHA still needs independent checking.


- **2026-10-21**: PR #181 strict hosted probe merged; GitHub run 39650367492 reported `web_healthy`, `storage_ready` and `three_markets_running`. Paper Cycle run 39659602972 completed `skipped_recent_cloudflare`, not an additional paper execution. Current branch `feat/paper-performance-evidence-gate` adds a **read-only** paper PnL sample-coverage diagnostic (30 known PnL events, >=95% coverage). Neither sample size nor positive PnL alone establishes profitability. Exact Render deployment SHA is not verified in this step.

- Central AI repo-map generation is configured through dbrckk/repo-standards.
- Hosted paper runtime uses durable PostgreSQL persistence, bounded catch-up, a read-only Render dashboard, and an authenticated external scheduler endpoint.
- The Cloudflare paper scheduler deployment path is configured and has deployed successfully; the GitHub paper-cycle schedule remains enabled as fallback.
- PR #43 fixed the paper runtime daily-loss baseline so it persists across bars within the same trading day and resets only on a new trading day.
- PR #44 added a leakage-safe ensemble challenger evaluator trained only on labels observable by the signal bar.
- PR #45 wired the ensemble challenger into paper cycles as an opt-in shadow observer. River remains the only model that can drive the RiskEngine and paper execution.
- An earlier hosted deployment was verified with `AI_TRADING_SHADOW_CHALLENGER=1` and `AI_TRADING_MARKETS=GC=F,^GDAXI,BTC-USD`; the current Render deployed SHA still requires independent verification.
- PR #47 enriched only the shadow challenger to 14 features while keeping the production River feature set unchanged.
- PR #48 aggregates River and challenger accuracy, Brier-style calibration error, directional edge, and composite quality from durable audit evidence and exposes it through `/api/overview`.
- PR #49 adds a review-only eligibility gate requiring sustained evidence before a challenger can even be considered for promotion; it does not promote models automatically.
- PR #50 introduced independent Gold/DAX/BTC paper runtimes, isolated market failures, a normalized 100k portfolio view (34%/33%/33%), `/api/markets`, responsive market cards, and cross-market recent trades.
- PR #51 made Gold/DAX/BTC cycle execution concurrent and added per-market signal/confidence telemetry.
- PR #52 made volume-less index data safe, unblocking the DAX runtime.
- PRs #54-#61 upgraded the premium dashboard, fixed scroll-safe live refresh, introduced the leakage-safe 5m/15m/1h/4h MTF shadow, isolated its long history, bounded its compute window, reduced it to a 15-minute research cadence, added cycle-latency telemetry, and required directional evidence.
- PR #63 refined the MTF benchmark toward confidence-gated directional evidence.
- PR #66 added per-market leakage-safe parameter selection. Latest validated research result: Gold uses 45m / 5bp / ATR 0.25 / train 1000 / confidence 56%; DAX uses 45m / 5bp / ATR 0.25 / train 1000 / confidence 60%; BTC has no candidate that passes the directional gate, including the focused 45m/60m/90m search.
- PR #67 prepares those validated Gold/DAX configurations as versioned audit-only MTF candidates, resets their quality evidence logically by config name, and leaves BTC MTF disabled until a benchmark candidate passes.

- PR #173 merged on 2026-10-21: opt-in 5m River-v2 forward observer for Gold/DAX/BTC: fresh completed-bar gating, strictly matured-label bounded OVR training, atomic audit predictions, and next-cycle delayed v1/v2 directional scoring exposed read-only. **PR-head and post-merge main CI/CodeQL passed. Render /livez exact-deployment SHA verified on 2026-10-21.** River-v1 continues paper execution and v2 is not an approved trading signal.

- 2026-10-21 live Render probe at SHA `9f8d88ca`: `/livez` and `/readyz` healthy, three paper markets `RUNNING`, no market errors, 20 successful recent Cloudflare deliveries; however River-v2 `pending=0`/`observations=0` for Gold/DAX/BTC. Suspected reason: Yahoo's leading-edge 5m OHLC can be unfinished, making the River-v2 forward gate reject it. A targeted branch `fix/skip-unclosed-five-minute-bars` discards such mutable provider rows **before** paper execution and forward prediction. CI and deployed SHA verification still required; no profitability evidence.

- **2026-10-21 operational incident:** despite green PR #175 CI and positively verified Render release `b8669a71`, all three paper market statuses remained `STARTING` for over eleven minutes after a Cloudflare cycle began; the latest confirmed successful delivery was `2026-10-21T09:46:41Z`. The cause is not confirmed; potentially expensive newly unlocked River-v2 research was not isolated behind its own opt-in. Emergency `fix/river-v2-forward-compute-budget` isolates it with `AI_TRADING_RIVER_V2_SHADOW=0` by default, no disabled audit scan, and bounded optional OVR work (128 rows/3s). No success or recovery claim until live release and scheduler are rechecked.

- **2026-10-21 direct recovery verification:** Render `/livez` deployed SHA `59e1610b`; `/readyz` storage healthy; Gold 514, DAX 205, BTC 536 processed paper bars, all engines `RUNNING` and zero consecutive cycle errors. The latest 20 observed Cloudflare deliveries succeeded; last delivery `2026-10-21T16:16:23Z`. River-v2 remains `disabled` on all three markets. Gold and BTC latest **signal** states were `DELAYED`; DAX session was closed. The earlier persistent `STARTING` incident has therefore recovered operationally, but model profitability is not demonstrated. Portfolio paper realized PnL was approximately -0.57481 on eight trades.
- **PR #181 merged** (`a02c2a6`) on 2026-10-21: the scheduled GitHub Hosted Dashboard Probe now fails when any Gold/DAX/BTC paper engine is `STARTING`, `STALE`, `ERROR` or has consecutive cycle errors. PR-head CI and CodeQL passed. **Strict post-merge live health verification:** GitHub Actions run `39650367492` finished `success` on merged SHA, with log `PASS /livez: web_healthy`, `PASS /readyz: storage_ready`, `PASS /api/markets: three_markets_running` at `2026-10-21T18:10:56Z`. This read-only check confirms all three paper engines operational at the probe time, but did **not** check an expected deployment SHA; Render release parity remains unverified. No live trades or model promotion.

- **PR #180 merged on 2026-10-21** (`b74881b`): River-v2 forward diagnostic now exposes matured directional labels and confidence-gated v1/v2 directional predictions. Its sample-size threshold is not model promotion or trading evidence. PR CI and CodeQL passed. New follow-up `fix/probe-running-market-status` upgrades the GitHub hosted probe so green requires all Gold/DAX/BTC engines `RUNNING`, with no consecutive cycle errors; prior probes only checked portfolio completeness and could wrongly pass with all three engines `STARTING`. This change is read-only, requires CI/CodeQL, and does not establish new Render deployment verification.

- **PR #178 merged** on 2026-10-21: reviewer-only guard now requires 100 realized directional labels and 50 confident directional challenger predictions, on top of the pre-existing ensemble (250) and MTF (500) observation and quality thresholds. API/dashboard evidence counts and existing tests updated; PR CI and CodeQL passed. **Public Render still served old release SHA `59e1610b` on latest post-merge probe**; merged application code is not yet verified deployed. No paper trade decision or live-order path changed.

- After #178 merge, an independent live check of Render found all three engines `RUNNING` (Gold 517, DAX 205, BTC 539 processed paper bars), zero consecutive errors, latest confirmed Cloudflare delivery `2026-10-21T16:31:24Z` and 20 recent successes. The public deployed SHA was still `59e1610b`, so verify the new `6009f0bf` release before claiming its UI and review thresholds are live. River-v2 remains disabled, Gold signal delayed, DAX session closed and BTC at NO_TRADE.

## Broken / blockers
- Paper execution is operational on three markets, but the realized trade sample is statistically insufficient for quality or profitability claims.
- Free Render/Neon resources and occasional provider failures remain operational constraints; keep the hourly GitHub fallback.

## Current priority
- On 2026-10-20 a direct read-only hosted probe found `/livez.web_healthy=true`, `/readyz.ready=true`, three `RUNNING` paper markets, no market errors, eight paper trades and portfolio realized PnL approximately -0.57481 (normalized portfolio simulation units), with 20 successful recent Cloudflare deliveries. This proves runtime health, not current release SHA or trading edge.
- PR #169 **merged and verified on Render**: public `/livez.deployed_commit` exactly matches release SHA `5e0ea79388915b0b357917896ec8ac2e687e1b27`; `/readyz` confirms healthy storage, `/api/markets` reports Gold/DAX/BTC all RUNNING with no errors, and `/api/scheduler` reports 20 consecutive Cloudflare successes. The optional SHA-aware probe fails closed on absent or mismatching deployments. No trading logic or paper state migrated.
- PRs #166 and #167 are merged: hosted external heartbeat uses the 15-minute Cloudflare cadence while bar signals expire independently; dashboard session-expiry checks now use a deterministic time in CI.
- PR #157 is merged as **offline research tooling only**. It adds genuine pinned upstream Kronos-mini inference and a corrected three-class River One-vs-Rest comparator without changing persisted River-v1 paper execution.
- Latest real BTC-USD 5-minute Kronos smoke (2026-10-20, 40 windows, 29 directional) returned mean net Kronos **-0.0547%** per window, momentum **-0.0973%**, research River **+0.0041%**. Confidence lower bounds are negative and `review_eligible=false`; no profitable-trading claim or Kronos promotion is justified.
- Model-v1 limitation: the active binary logistic classifier has zero SHORT probability. Any three-class production migration requires an independently validated v2 state/model codec and controlled rollout, not a silent joblib rewrite.
- Verify the **actual** Render deployment revision and read-only `/api/markets` behavior; the successful GitHub hosted probe alone confirms availability, not deployed SHA.
- Preserve the free-tier Cloudflare/Render/Neon architecture and hourly GitHub fallback. Live order routing remains off.

- River-v2 versioned artifact work was merged in **PR #171**: the production v1 codec now refuses v2 subclasses, and a separate `joblib-river-ovr-v2` research codec round-trips only trusted ternary OVR models. This is **offline research only**, with no changes to paper runtime keys, persisted v1 states or live routing. Forward shadow is not yet installed; isolated read-only evaluation and independent evidence are next. PR-head CI and CodeQL passed.

- Read-only Render verification on 2026-10-21: initial `/livez.deployed_commit` was old `3c2bf9c1`, but the later direct probe **confirmed deployed commit `6f3fe1df` exactly**, matching merged PR #173, with `/livez.web_healthy=true` and `/readyz.ready=true`/`storage_healthy=true`. The new `overview.river_v2_shadow` fields were present for Gold, DAX, BTC, all non-actionable, with **0 matured observations** immediately after rollout. All three market statuses were transiently `STARTING` during the paper cycle, with zero market errors; verify normal return to `RUNNING` on a later probe. No new model evidence or profitable trade claim.

## Validation
- Main after PR #167: Ruff/Pytest/Cloudflare Worker checks and CodeQL passed (run 39499994723 and 39499994605).
- PR #157 final head: CI run 39500880135, CodeQL run 39500880125 and actual pinned Kronos model smoke run 39500872405 all passed, with JSON artifact 12301525143.
- PR #169 head and main post-merge CI, CodeQL and hosted dashboard probe passed. Direct Render `/livez` deployed SHA matched the intended release; `/readyz`, `/api/markets` and `/api/scheduler` validated read-only.
- Canonical validation: `ruff check src tests`, full Pytest against PostgreSQL 16, Cloudflare Worker tests and CodeQL.

## Last verified
- 2026-10-20

<!-- AUTO:START -->
## Automatic repository state

Generated: 2026-10-23T10:23:55Z

### Git
- Branch: `main`
- Head: `89ffef0ec03e`
- Commit date: 2026-10-23T06:23:44-04:00
- Commit: fix(research): reject incomplete or invalid backtest performance data
- Tracked files: 515

### Recently changed files
- `README.md`
- `src/ai_trading/performance.py`
- `tests/test_performance.py`
- `src/ai_trading/promotion.py`
- `src/ai_trading/soak_gate.py`
- `tests/test_multi_period_promotion.py`
- `tests/test_promotion.py`
- `tests/test_soak_gate.py`
- `src/ai_trading/portfolio_risk.py`
- `tests/test_portfolio_risk.py`
- `src/ai_trading/risk_governor.py`
- `tests/test_risk_governor.py`
- `src/ai_trading/config.py`
- `src/ai_trading/risk.py`
- `tests/test_config_validation.py`
- `tests/test_risk.py`

### Project signals
- `pyproject.toml`
- `Dockerfile`

> Generated by dbrckk/repo-standards. Keep manual priorities and blockers outside the AUTO markers.
<!-- AUTO:END -->

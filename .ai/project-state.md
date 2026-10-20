# Project state

Status: active

## Working
- Central AI repo-map generation is configured through dbrckk/repo-standards.
- Hosted paper runtime uses durable PostgreSQL persistence, bounded catch-up, a read-only Render dashboard, and an authenticated external scheduler endpoint.
- The Cloudflare paper scheduler deployment path is configured and has deployed successfully; the GitHub paper-cycle schedule remains enabled as fallback.
- PR #43 fixed the paper runtime daily-loss baseline so it persists across bars within the same trading day and resets only on a new trading day.
- PR #44 added a leakage-safe ensemble challenger evaluator trained only on labels observable by the signal bar.
- PR #45 wired the ensemble challenger into paper cycles as an opt-in shadow observer. River remains the only model that can drive the RiskEngine and paper execution.
- Render is live on commit `3e40c11` with `AI_TRADING_SHADOW_CHALLENGER=1` and `AI_TRADING_MARKETS=GC=F,^GDAXI,BTC-USD`.
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

## Broken / blockers
- Paper execution is operational on three markets, but the realized trade sample is statistically insufficient for quality or profitability claims.
- Free Render/Neon resources and occasional provider failures remain operational constraints; keep the hourly GitHub fallback.

## Current priority
- PR #165 aligns cross-market realized PnL, gross profit/loss and drawdown with the 34%/33%/33% portfolio allocations. Per-market normalized 100k histories and River execution stay unchanged.
- On 2026-10-20 production had 8 paper fills; cross-market unweighted realized PnL was about -1.67 simulation units, while the allocation-adjusted result is -0.575. Verify deployed /api/markets and dashboard after green CI and merge.
- Keep monitoring authenticated Cloudflare delivery and the GitHub fallback. Recent cycles are healthy; scheduler telemetry verified at least 20 consecutive successful Cloudflare deliveries.
- Continue leakage-safe out-of-sample evaluation of Gold/DAX/BTC and shadow-only Kronos benchmarking. Do not promote challengers based on too few trades or activate live orders.

## Validation
- Canonical validation: ruff check . and pytest with PostgreSQL integration service; Cloudflare Worker tests and CodeQL must remain green.
- The allocation-adjusted SQL was run read-only on Neon, yielding 8 events, realized PnL -0.574810634, gross profit 1.211721732, gross loss 1.786532367 and max drawdown 1.490124683.
- PR #165 CI, CodeQL and deployment evidence pending at time of writing.

## Last verified
- 2026-10-20

<!-- AUTO:START -->
## Automatic repository state

Generated: 2026-10-20T00:32:12Z

### Git
- Branch: `main`
- Head: `24b4eb263e09`
- Commit date: 2026-10-19T20:32:02-04:00
- Commit: fix(paper): isolate concurrent Gold, DAX and BTC runtime locks (#164)
- Tracked files: 504

### Recently changed files
- `src/ai_trading/runtime.py`
- `tests/test_runtime_lock.py`
- `.github/workflows/paper-cycle.yml`
- `README.md`
- `src/ai_trading/scheduler_fallback.py`
- `tests/test_paper_cycle_workflow.py`
- `infra/cloudflare-paper-scheduler/src/index.js`
- `infra/cloudflare-paper-scheduler/test/index.test.js`
- `src/ai_trading/multi_market.py`
- `src/ai_trading/scheduler_endpoint.py`
- `tests/test_multi_market.py`
- `tests/test_scheduler_endpoint.py`
- `src/ai_trading/postgres_persistence.py`
- `tests/test_postgres_persistence.py`

### Project signals
- `pyproject.toml`
- `Dockerfile`

> Generated by dbrckk/repo-standards. Keep manual priorities and blockers outside the AUTO markers.
<!-- AUTO:END -->

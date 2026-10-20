# Project state

Status: active

## Working
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

## Broken / blockers
- Paper execution is operational on three markets, but the realized trade sample is statistically insufficient for quality or profitability claims.
- Free Render/Neon resources and occasional provider failures remain operational constraints; keep the hourly GitHub fallback.

## Current priority
- PRs #166 and #167 are merged: hosted external heartbeat uses the 15-minute Cloudflare cadence while bar signals expire independently; dashboard session-expiry checks now use a deterministic time in CI.
- PR #157 is merged as **offline research tooling only**. It adds genuine pinned upstream Kronos-mini inference and a corrected three-class River One-vs-Rest comparator without changing persisted River-v1 paper execution.
- Latest real BTC-USD 5-minute Kronos smoke (2026-10-20, 40 windows, 29 directional) returned mean net Kronos **-0.0547%** per window, momentum **-0.0973%**, research River **+0.0041%**. Confidence lower bounds are negative and `review_eligible=false`; no profitable-trading claim or Kronos promotion is justified.
- Model-v1 limitation: the active binary logistic classifier has zero SHORT probability. Any three-class production migration requires an independently validated v2 state/model codec and controlled rollout, not a silent joblib rewrite.
- Verify the **actual** Render deployment revision and read-only `/api/markets` behavior; the successful GitHub hosted probe alone confirms availability, not deployed SHA.
- Preserve the free-tier Cloudflare/Render/Neon architecture and hourly GitHub fallback. Live order routing remains off.

## Validation
- Main after PR #167: Ruff/Pytest/Cloudflare Worker checks and CodeQL passed (run 39499994723 and 39499994605).
- PR #157 final head: CI run 39500880135, CodeQL run 39500880125 and actual pinned Kronos model smoke run 39500872405 all passed, with JSON artifact 12301525143.
- Main-after-#157 CI and deploy verification are tracked separately; do not claim success from prior branch runs.
- Canonical validation: `ruff check src tests`, full Pytest against PostgreSQL 16, Cloudflare Worker tests and CodeQL.

## Last verified
- 2026-10-20

<!-- AUTO:START -->
## Automatic repository state

Generated: 2026-10-20T21:34:07Z

### Git
- Branch: `main`
- Head: `081b34ec8874`
- Commit date: 2026-10-20T17:33:57-04:00
- Commit: feat(research): add validated offline Kronos vs multiclass River benchmark (#157)
- Tracked files: 507

### Recently changed files
- `.github/workflows/kronos-model-smoke.yml`
- `README.md`
- `docs/kronos-research.md`
- `src/ai_trading/kronos_research.py`
- `src/ai_trading/online.py`
- `tests/test_online.py`
- `tests/test_paper_cycle.py`
- `src/ai_trading/dashboard.py`
- `tests/test_dashboard_engine_status.py`
- `src/ai_trading/file_persistence.py`
- `src/ai_trading/multi_market.py`
- `src/ai_trading/performance_metrics.py`
- `src/ai_trading/persistence.py`
- `src/ai_trading/postgres_persistence.py`
- `tests/test_cumulative_performance_persistence.py`
- `tests/test_multi_market.py`
- `src/ai_trading/runtime.py`
- `tests/test_runtime_lock.py`

### Project signals
- `pyproject.toml`
- `Dockerfile`

> Generated by dbrckk/repo-standards. Keep manual priorities and blockers outside the AUTO markers.
<!-- AUTO:END -->

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
- Render request logs do not expose the scheduler POST evidence needed to directly prove three consecutive Cloudflare heartbeats, so issue #40 remains open.
- GitHub scheduled paper-cycle delivery has historically been sparse; keep it as fallback until the Cloudflare acceptance evidence is complete.
- Repository-standards routing benchmark health is separate from the trading CI; trading CI is green.

## Current priority
- Collect new versioned MTF evidence independently for the validated Gold and DAX 45-minute candidates.
- Require at least 500 realized MTF observations and at least 100 directional observations before MTF review eligibility.
- Keep BTC MTF unvalidated/disabled until a leakage-safe benchmark candidate passes the active-direction gate.
- Keep River authoritative and every challenger strictly observational until sustained out-of-sample improvement is demonstrated.
- Keep production paper-only and retain the GitHub scheduled fallback until issue #40 acceptance criteria are fully evidenced.

## Validation
- Canonical validation: `ruff check .` and `pytest`.
- Cloudflare Worker tests must remain green.
- PR #43, #44, #45, #47, #48, #49, #50, #51, and #52 are merged and passed the trading CI before production activation.
- Live runtime remains `RUNNING` with zero consecutive cycle errors.

## Last verified
- 2026-09-20

<!-- AUTO:START -->
## Automatic repository state

Generated: 2026-09-20T19:15:42Z

### Git
- Branch: `main`
- Head: `6c376ef15698`
- Commit date: 2026-09-20T21:15:30+02:00
- Commit: fix: align MTF evidence cadence with candidate horizon (#70)
- Tracked files: 477

### Recently changed files
- `src/ai_trading/paper_cycle.py`
- `tests/test_paper_cycle.py`
- `src/ai_trading/mtf_shadow_config.py`
- `tests/test_dashboard_overview.py`
- `tests/test_mtf_shadow_config.py`
- `tests/test_multi_market.py`
- `.github/workflows/mtf-parameter-benchmark.yml`
- `src/ai_trading/mtf_parameter_benchmark.py`
- `tests/test_mtf_parameter_benchmark.py`
- `src/ai_trading/dashboard.py`
- `src/ai_trading/file_persistence.py`
- `src/ai_trading/mtf_shadow_challenger.py`
- `src/ai_trading/mtf_shadow_quality.py`
- `src/ai_trading/operational_overview.py`
- `src/ai_trading/postgres_persistence.py`
- `tests/test_mtf_shadow_challenger.py`
- `tests/test_mtf_shadow_quality.py`

### Project signals
- `pyproject.toml`
- `Dockerfile`

> Generated by dbrckk/repo-standards. Keep manual priorities and blockers outside the AUTO markers.
<!-- AUTO:END -->

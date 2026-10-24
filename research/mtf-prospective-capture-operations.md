# Prospective MTF capture — pre-cutoff operational schedule decision

Recorded **2026-10-24**, before the locked first eligible bar on **2026-10-26 00:00 UTC**.

## Schedule

- GitHub Actions `Prospective MTF Bar Capture` runs **Monday–Friday at 18:31 UTC** (`31 18 * * 1-5`), starting with the first applicable date on 2026-10-26.
- Earlier draft execution at **02:31 UTC every calendar day** was corrected *before* any post-cutoff observation existed. That hour precedes Xetra's regular daytime trading session and would yield an expected zero completed DAX bars on the study's first Monday. The weekend schedule would likewise repeatedly produce no DAX cash-session candles.
- Xetra's normal trading hours are Monday–Friday 09:00–17:30 Central European local time, subject to local exchange holidays. See the official Deutsche Börse trading calendar: https://www.cashmarket.deutsche-boerse.com/cash-en/trading/trading-calendar-and-trading-hours
- At 18:31 UTC, the normal DAX cash session has finished across both European standard and daylight time. This schedule does **not** guarantee Yahoo 5m availability or completeness; provider/validation failures remain visible and the collector must fail closed.
- BTC-USD trades on weekends. On Monday, the pinned Yahoo acquisition window `5d` can capture weekend BTC bars that have completed and aged by at least the configured provider lag. Weekend observations must not be discarded during research evaluation merely because weekend workflow runs are omitted. Check source timestamp continuity and revisions independently.
- The `workflow_dispatch` route still permits manual archive-only audit captures, with run ID, captured-at UTC and commit fingerprints.

## Frozen boundaries and prohibited actions

The original preregistration at `research/mtf-prospective-2026-10-26-v1.json` stays byte-for-byte unchanged, with SHA-256 `7b8870cce74d7941ed6e3f3c33e0829cd28b2d92f32d11ab5ca8309daf48b096`. The eligible opening timestamp must be at or after **2026-10-26 00:00 UTC**, and each 5-minute candle must have completed and aged for 15 additional minutes before archival. Gold/DAX/BTC, provider, frozen comparators and assumed costs are unchanged.

This is a **pre-observation operations fix**, not a strategy-selection or performance-driven schedule change. No model fitting, parameter tuning, promotion, production persistence write or trading order may use this archive process. GitHub Action artifacts expire (currently 90 days); availability of long-term independently retained archives is **not established**.

## Expected audit behavior

An exchange holiday can leave only earlier completed DAX candles within the retained 5-day retrieval window. The collector records those historical-within-study bars without claiming a same-day cash session; reviewers must inspect the per-market last timestamp and detect holidays and calendar gaps independently. Missing or invalid provider data, or a truly empty future-only dataset for any required market, must instead produce a diagnostic manifest and a failed all-market capture. No exchange-calendar freshness gate is implemented. A green archived snapshot confirms valid collected data under these checks, **not** economic value, real fill quality or live-trading readiness.

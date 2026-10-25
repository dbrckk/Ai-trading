# Prospective MTF evaluation — rules frozen before the first eligible observation

Recorded on **2026-10-25**, before the original capture study begins on **2026-10-26 00:00 UTC**. The machine-readable preregistration is [mtf-prospective-evaluation-2026-10-26-v1.json](mtf-prospective-evaluation-2026-10-26-v1.json). This is an **evaluation plan**, not a finding of profit or approval to trade.

## Hard boundary between archived candles and forward predictions

The existing `Prospective MTF Bar Capture` workflow archives only Yahoo 5-minute OHLCV and source fingerprints. It **does not archive contemporaneous challenger model forecasts**. Therefore source OHLCV can establish temporal data quality, but **cannot on its own establish genuinely forward-logged predictive accuracy or trading profitability**. Running a model retrospectively across the now-known future bars and calling it prospective would be data leakage.

A separate, **twice-hourly River-v1 paper observer** now archives dashboard-reported predictions after a read-only GET (at UTC minutes 07 and 37). The scheduling frequency was set before the first prospective bar to improve Gold/DAX cash-session coverage; a scheduled run is still best-effort, and repeated market signals are not independent trials. These are **not predictions of any frozen MTF comparator**, and its report must distinguish: (a) a time-valid market forecast, including a risk-rejected or FLAT observation, from (b) an approved hypothetical paper **entry**. The archive fields `eligible_markets` and `paper_entry_eligible_markets` record those distinct counts; they are not filled-order or realized-PnL counts. The observer stops at the registered 2027-01-24 00:00 UTC boundary. A GitHub workflow run may be delayed or omitted; do not impute missed hourly forecasts.

For any future genuine forward evaluation, each candidate forecast must first be durably archived with its generation timestamp, frozen comparator and model/code identity, direction/confidence and the latest historical candle it could see. Forecasts recorded **after their entry or horizon result was observable** are excluded. If this evidence is absent, the economic and classification metrics are **not evaluable**. No fitting, threshold selection or configuration tuning is authorized using these future observations. The original OHLCV capture registration and its SHA-256 are unchanged.

## Fixed assessment window and decision gates

The planned evaluation is an observation window of **90 calendar days**, `2026-10-26T00:00Z` inclusive through `2027-01-24T00:00Z` exclusive. The original **three frozen** Gold, DAX and BTC comparators, costs of 2 bps transaction + 1 bp slippage **per side**, next-open entry and horizon-close exit are retained. The economic readouts require non-overlapping hypothetical positions, per-market and shared-capital net results and drawdown.

The protocol predefines minimum data/forecast/trade evidence and requires positive after-cost results for **all three** markets and a shared account to qualify for *further review*. Passing would **still not authorize** a live broker or automatic model promotion: FX, contracts/multipliers, realistic spread, funding, leverage and real fills are not validated. Failed or missing conditions produce a negative or inconclusive study — never a silent parameter change. Avoid choosing the best of three variants after seeing the prospective outcomes and reporting it as if it were independently selected.

## Source gaps and 90-day artifact retention

Market closures, holidays, gaps, revisions and provider delays must be reported rather than silently filled or rewritten. The first daily-run archive will generally occur after Europe's session and is *not* a guarantee of complete 5-minute continuity. GitHub Actions artifacts have a **90-day retention setting**, so original early captures may expire near the final assessment. Durable independent archiving **has not been established**. If original archives or timestamped forecast records cannot be verified at assessment, report the outcome as **inconclusive**, not profitable.

This preregistration does not change River-v1 paper authority, scheduler behavior, the registered OHLCV collection boundary, or live brokerage status.

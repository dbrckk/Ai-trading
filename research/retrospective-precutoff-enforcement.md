# Retrospective research cutoff — leakage protection

Effective after the frozen 2026-10-26T00:00:00Z start of the prospective Gold/DAX/BTC 5-minute study.

## Why this guard exists

The historical research workflows previously requested `period=1mo` from Yahoo on every run. After the prospective study starts, a rolling month includes candles that did not exist before the frozen holdout boundary. Feeding those candles into MTF ensemble fitting, parameter selection or the historical turnover threshold search would undermine the independence of the prospective evaluation.

The research-only `frozen_preprospective_history` helper now excludes all candles whose **UTC opening time is at or after 2026-10-26T00:00:00Z**. It rejects naive or malformed timestamps, fails if the provider has no remaining pre-cutoff history, and does not silently backfill missing older bars.

The guard is applied to three historically selecting entrypoints: `python -m ai_trading.mtf_parameter_benchmark`, the `turnover-study` CLI, and the `MTF Net Cost Evidence` GitHub workflow. The scheduled prospective OHLCV capture and read-only River-v1 forward observer **are not changed**, and no frozen comparator is retuned. The 1x/2x/3x cost stress is purely retrospective.

## Operational caveats

Yahoo's short intraday retention may eventually leave insufficient pre-cutoff 5-minute candles for a rerun. In that case the research job must **fail or mark the market unavailable**; it may not substitute later prospective bars or claim a reproducible old holdout. Durable reproducible historical datasets are not currently established. The original study's future-data archive remains the evidence source for prospective assessment, not for retrospective tuning.

This is a research integrity fix, not evidence of higher win rate, positive profit, or live broker readiness.

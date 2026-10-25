# Forward-logged paper signals (separate from frozen MTF study)

Created **2026-10-25**, before the observation cutoff of **2026-10-26 00:00 UTC**.

The `Forward Paper Signal Evidence` GitHub Action is a **read-only public dashboard observer**. Starting after the cutoff, it attempts one snapshot per hour at minute 07 UTC, through the preregistered end boundary of **2027-01-24 00:00 UTC** (the workflow skips collection and upload thereafter). GitHub scheduled events can be delayed, skipped or disabled; an absent snapshot is a **missing observation**, never a reason to fabricate one after the fact. The workflow records a GitHub run ID, capture Git SHA, deployed Render SHA, timestamps and SHA-256 of the raw public JSON responses. No secrets, trading orders, model training or production persistence write are required.

## What is — and is not — recorded

The dashboard's paper model is **River-v1**, not the three frozen MTF challenger comparators. The observer copies only the paper market's live public signal, its confidence, risk approval and an intentionally truncated model checksum when the market is RUNNING, session open, signal valid and no more than 15 minutes old. Market closures, delayed model decisions and missing model fingerprints are stored without an eligible directional signal. Signal timestamps are **not rewritten**.

An observation is timestamped **after** the dashboard response is received. Its earliest *hypothetical* entry is the following complete UTC 5-minute opening timestamp **strictly later** than recording. This is a research-only forward reference; it is **not the same execution** as the model's original (earlier) paper signal. It does not guarantee market-session availability or real fills, and a future research evaluator must still obtain an independently archived eligible entry/open and eventual outcome.

## Critical scientific distinction

These logs may enable a **separate prospective audit of exposed River-v1 paper signals**, but **cannot qualify the frozen MTF comparators**. River-v1 may learn online in ordinary paper operation, model hashes are only public truncated identifiers, and forecasts are not a pinned model over the frozen 90-day horizon. Do not claim MTF predictions, a globally untouched holdout, realized PnL, model promotions or live-broker eligibility based on this workflow. The frozen OHLCV registration and separate evaluation protocol are unchanged.

## Retention and privacy

Each hourly GitHub Actions run uploads an independently validated JSON artifact with **90-day retention**. This is **not durable beyond 90 days**. A long-term authorized private evidence store and lifecycle audit are still needed before final-study claims. The workflow observes only the already-public dashboard without POST requests or scheduler triggering.

On failure, the collector exits nonzero rather than inventing a historical signal; its error message contains no remote response body. Manual workflow dispatch is permitted for read-only diagnostics. Pre-cutoff executions skip all remote requests and emit an auditable `awaiting_cutoff` placeholder.

The observer is deliberately separate from the production paper cycle and cannot place orders.

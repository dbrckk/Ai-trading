# Kronos: isolated research challenger

The upstream [shiyu-coder/Kronos](https://github.com/shiyu-coder/Kronos) uses pre-trained
financial OHLCV models. This integration calls the **original KronosPredictor**
and keeps PyTorch and model downloads outside the production Render/Cloudflare
runtime. It does not alter River paper trades or promote a new model.

## Run it (Python 3.11+, separate environment recommended)

```bash
git clone https://github.com/dbrckk/Ai-trading.git
git clone https://github.com/shiyu-coder/Kronos.git
git -C Kronos checkout --detach 67b630e67f6a18c9e9be918d9b4337c960db1e9a
cd Ai-trading
python -m venv .venv
source .venv/bin/activate
pip install -e .
pip install -r ../Kronos/requirements.txt
python -m ai_trading.kronos_research \
  --kronos-source ../Kronos \
  --symbol BTC-USD --period 60d --interval 5m \
  --model-size mini --lookback 256 --horizon-bars 9 \
  --max-windows 40 --sample-count 3 \
  --transaction-cost-bps 3 --slippage-bps 2 \
  --output artifacts/kronos-btc-45m.json
```

The optional GitHub Actions workflow `Kronos Model Smoke` runs the pinned
upstream `mini` implementation against real BTC-USD data and uploads a JSON
artifact. It performs only a few predictions to verify interoperability,
not enough to establish predictive quality.

The upstream tokenizer and model weights download from Hugging Face on first
use. `mini` is the lightweight option; choose `small` or `base` for a larger
model. The script uses CPU by default (`--device cpu`). A larger model is **not**
automatically better and has not been validated on our markets.

Repeat the research independently for `GC=F`, `^GDAXI` and `BTC-USD`.
For historical 5-minute data older than a provider permits, pass
`--csv path/to/history.csv` instead of using Yahoo; CSV columns:
`timestamp,Open,High,Low,Close,Volume`. Timestamp must be parseable as UTC
or include an offset. Do not use adjusted/revised historical bars unavailable
at the time of prediction when claiming a historical simulation.

## Evidence and limitations

- Every sample uses only `lookback` completed OHLCV bars, ending at the
  signal close. The future prediction timestamps are extrapolated from the
  last observed bar cadence; windows crossing market closures or missing
  bars are excluded. **Future OHLCV values are not given to Kronos**.
- Entry is simulated at the next bar's **open**, and exit at the horizon
  bar's **close**. Round-trip transaction cost and slippage are charged.
- Samples do not have overlapping holding periods. All three comparators
  (real pretrained Kronos, same-horizon momentum, and a *research-only*
  three-class River One-vs-Rest classifier) use identical realized
  next-open-to-horizon-close returns and the same explicit round-trip costs.
- The River research comparator is trained sequentially using only labels
  whose `horizon_bars` outcome is already observable at the signal close.
  Its minimum confidence is 0.56 by default (configurable), as in the
  existing production risk threshold; its model is **not** promoted to
  production by the study.
- The existing persisted `joblib-river-v1` engine uses binary logistic
  regression even though it expects three classes; its SHORT probability
  is zero under its current probability mapping. The research River
  comparator corrects this by using One-vs-Rest, **without overwriting
  or silently migrating** existing production state.
- JSON contains every timestamp, forecast direction, realized outcome, net
  return and summary. No synthetic/mock prediction is used in real runs.
- `review_eligible` can only be true with at least 500 non-overlapping
  evaluated windows, 100 directional predictions, and positive lower 95%
  bootstrap bounds for net mean return **and** incremental return over
  *both momentum and the corrected River research comparator*. This is
  **review eligibility**, never automatic promotion.
- This baseline is **not** the active persisted River-v1 model; its
  evaluation is an offline controlled comparison under the same horizon.
  Historical window selection and fixed thresholds are not a replacement
  for a fully purged independent holdout or **live forward shadow**
  evaluation.
  Retrospective exclusion of session gaps can still introduce selection bias.
- Simulated next-open fills omit intrabar spread dynamics, market impact,
  financing and liquidity constraints. Results **cannot demonstrate**
  profitable live execution or materially improved trades.

## Paper challenger review: minimum directional evidence

The existing **ensemble 5m shadow** and validated **multi-timeframe
shadow** are evaluated in parallel with the River-v1 paper engine. A
high raw accuracy can be misleading when a challenger frequently
predicts FLAT/NO_TRADE, so review eligibility now requires **all**
of the following:

- Ensemble 5m: at least **250** matched realized samples, **100**
  realized directional labels (LONG or SHORT), and **50 confident
  directional challenger predictions**. For the ensemble comparison,
  a directional prediction must have confidence of at least **0.56**.
- MTF: at least **500** matched realized samples, **100** realized
  directional labels, and **50** challenger directional predictions
  after the candidate's own versioned minimum-confidence gate.
- Previously existing composite-score improvement, accuracy,
  calibration and directional-edge non-degradation checks **still
  apply**. Invalid confidence values are excluded rather than
  counted toward any evidence threshold.

The live `/api/markets` model diagnostics expose the counts and
thresholds independently for each Gold, DAX and BTC market. The
dashboard shows both realized directional examples and confident
directional candidate predictions. These are **review-only
safeguards**, not proof of net-of-cost profitability or forward
validity. No challenger can place trades or promote itself, and
River-v2 remains disabled by default on Render.

## Isolated River-v2 research artifact

River-v2 uses `RiverMulticlassDirectionModel` (three-class One-vs-Rest)
rather than the production River-v1 binary logistic classifier. The
`research_model_codec` exposes `serialize_research_model` and
`deserialize_research_model` for **trusted offline artifacts only**,
labeled `joblib-river-ovr-v2`, version 2, with a payload checksum.
It preserves trained probabilities and observation counters across a
round trip. Joblib/pickle is **not safe for untrusted input**; a SHA-256
checksum detects corruption, not maliciously generated objects.

The production `model_codec` continues to accept **only the exact**
`RiverDirectionModel` and `joblib-river-v1`; it refuses River-v2
subclasses on write and v2 blobs on read. Neither existing PostgreSQL
paper runtime keys nor stored v1 model states are migrated. There is
**no** River-v2 activation path in hosted paper execution.

The existing walk-forward Kronos research comparator supplies offline
side-by-side evidence; there is not yet an independently verified,
persisted River-v2 **forward shadow** feed. Promotion would require
separate holdout and forward evidence, audited risk/short-position
handling, a versioned rollout and rollback protocol. Until then,
River-v2 is not an actionable trade signal.

## River-v2: first live-cycle forward observer (audit only)

River-v2 now requires **both** `AI_TRADING_SHADOW_CHALLENGER=1`
and a **separate explicit opt-in** `AI_TRADING_RIVER_V2_SHADOW=1`.
The new research flag defaults to **OFF** for the free Render worker,
even when the existing shadow challenger remains enabled. The
`/api/markets` River-v2 status then reads `disabled` and skips the
optional historical audit query. Do not enable this research path on
Render until CPU/scheduler latency is independently validated. When
explicitly enabled it observes **5-minute paper markets only**
(Gold, DAX and BTC), independently of River-v1 decisions:

- At most one v2 observation is attached to a cycle, and **only** if the
  latest completed provider candle has closed less than five minutes ago.
  The 5m paper-cycle input now **discards a still-forming Yahoo candle**
  before both River-v1 paper execution and River-v2 evaluation (with a
  two-second finality buffer). This prevents a mutable partial OHLC close
  from entering the committed paper model state. Stale and catch-up
  signals remain excluded. No future OHLCV
  is passed to the observer; it trains from up to 128 historical rows
  with labels matured before the observed signal. At least 100 valid
  training rows are required. A strict three-second compute budget applies
  per market on free-tier hosts: unfinished research is skipped rather
  than delaying the authoritative River-v1 paper cycle.
- A v2 side, confidence, three-class probabilities, model format/version,
  signal close, UTC observation time, label horizon, and training cutoff
  are appended to the **existing, atomic paper audit transaction** under
  `river_v2_shadow`. It does not persist/rewrite a v2 joblib model or
  change the v1 model key, paper positions, risk approvals or orders.
- Each later processed paper bar also records its actual
  `execution_close` price in the audit. The optional read-only
  `load_river_v2_forward_quality` reader joins v2 observations with
  later River-v1 decisions for the **same signal timestamp**, requiring
  an actual consecutive 5-minute bar and both v2 inference **and its
  durable audit commit** before the next bar closed. Missing, stale,
  late-committed or incomplete outcomes are excluded.
- Per-market `/api/markets` includes `overview.river_v2_shadow` with
  matured observations, pending observations, confidence-gated v2
  SHORT count and matching v1/v2 directional quality when at least
  five observations exist. It also reports **directional ground-truth
  labels** and **confidence-gated directional predictions** separately
  for River-v1 and River-v2; the evidence gate requires 250 matched
  observations, 100 directional outcomes and 50 confident River-v2
  directional predictions. Passing these counts is only a sample-size
  diagnostic, never an approval to trade or proof of positive returns.
  The data is read-only; if the storage is
  unavailable, the observer does not break the dashboard.
- Evaluation is directional classification, **not** executable
  next-open fills or net-of-cost returns. Real-world decision latency
  and market spread can erase apparent prediction accuracy. No automatic
  promotion exists and `eligible_for_review=false` until a separate
  statistically adequate holdout, forward audit and controlled rollout
  are implemented.

Because no separate River-v2 training state is persisted yet, it
retrains from a bounded recent window for each fresh observation.
A timed-out research run does **not** count as forward evidence; a long
hosted scheduler cycle remains an operational concern until completion
is independently verified.
**Do not infer increased profitability from this feature.**

## Forward shadow operational follow-up (2026-10-21)

A live read-only Render probe of deployed `9f8d88ca` verified `/livez`
and `/readyz`, Gold/DAX/BTC all `RUNNING`, zero market errors and 20
recent successful Cloudflare deliveries. Nevertheless
`overview.river_v2_shadow.observations=0` and `pending=0` for all
three markets: release health **did not prove** the observer was
producing real samples. The 5m input filter above addresses a specific
cause: Yahoo can include an unfinished leading-edge candle even when
the previous candle is complete. A successful CI after this change
is **not** equivalent to verified live River-v2 samples. Confirm the
actual deployed SHA, then look for >0 durably committed pending and
subsequently matured observations before assessing model quality.

## Observed BTC research smoke (2026-10-20)

The real original `Kronos-mini` workflow on BTC-USD 5-minute history succeeded
([workflow run 39500872405](https://github.com/dbrckk/Ai-trading/actions/runs/39500872405),
artifact `kronos-river-btc-smoke` ID `12301525143`). With 40 eligible,
non-overlapping windows, 29 Kronos directional predictions and common costs:

| Research comparator | Mean net return per evaluated window |
| --- | ---: |
| Kronos-mini | -0.0547% |
| Same-horizon momentum | -0.0973% |
| Corrected three-class River research baseline | +0.0041% |

All relevant 95% bootstrap lower confidence bounds were negative and
`review_eligible=false`. These 40 windows are **not** a held-out
statistically adequate validation, even though Kronos outperformed the
momentum baseline in this short run. The updated model is **not a trade
signal**: keep River-v1 paper-only execution unchanged and obtain independent,
held-out and forward-shadow results across markets before considering a new
model version.

Do not enable Kronos in execution, lower the current risk limits, or deploy
PyTorch on the scheduler merely because an offline benchmark scores well.

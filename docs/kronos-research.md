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
- Samples do not have overlapping holding periods, and the directional
  decision is compared with a same-horizon momentum baseline.
- JSON contains every timestamp, forecast direction, realized outcome, net
  return and summary. No synthetic/mock prediction is used in real runs.
- `review_eligible` can only be true with at least 500 non-overlapping
  evaluated windows, 100 directional predictions, and positive lower 95%
  bootstrap bounds for both net mean return and incremental return over
  momentum. This is **review eligibility**, never automatic promotion.
- Historical window selection and fixed thresholds are not a replacement for
  a fully purged, independent holdout, comparison with the incumbent River\n  model on identical bars, or **live forward shadow** evaluation.
  Retrospective exclusion of session gaps can still introduce selection bias.
- Simulated next-open fills omit intrabar spread dynamics, market impact,
  financing and liquidity constraints. Results **cannot demonstrate**
  profitable live execution or materially improved trades.

Do not enable Kronos in execution, lower the current risk limits, or deploy
PyTorch on the scheduler merely because an offline benchmark scores well.

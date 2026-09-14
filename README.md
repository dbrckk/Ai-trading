# Ai-trading

Autonomous, self-learning trading research platform.

## Goals

- ingest market data
- generate features
- learn from new observations
- produce autonomous LONG / SHORT / FLAT decisions
- enforce independent portfolio/risk constraints
- execute through a broker abstraction
- run in paper mode by default
- record every decision for later evaluation and retraining

The optimization target is **risk-adjusted profit after costs**, not raw backtest profit.

## Architecture

```
Market data -> Features -> Online model -> Signal
                                  |
                                  v
Portfolio state -> Risk engine -> Decision -> Broker
                                  |
                                  v
                            Audit / metrics
```

Initial implementation uses:
- `yfinance` for simple historical data
- `scikit-learn` SGDClassifier for incremental learning
- a deterministic paper broker
- walk-forward-compatible feature/label construction
- hard risk limits independent from the model

Future adapters are planned for components already ranked in the companion `star-list` catalog: QuantConnect/Lean, NautilusTrader, vectorbt, Qlib, River, Optuna, OpenBB, Riskfolio-Lib, skfolio and QuantStats.

## Quick start

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
ai-trading train --symbol GC=F --period 5y
ai-trading paper --symbol GC=F --period 1y
pytest
```

On Windows PowerShell:

```powershell
.venv\Scripts\Activate.ps1
```

## Safety defaults

Live order routing is intentionally absent from V0. The broker interface is designed for later adapters, but the only included broker is paper-only. Risk limits are applied after the model and cannot be bypassed by a strategy.

## Roadmap

1. V0: deterministic research + online model + paper broker + risk engine
2. V1: proper walk-forward backtester, transaction costs/slippage, experiment registry
3. V2: ensemble models + regime detection + Optuna
4. V3: event-driven execution adapter (NautilusTrader/Lean)
5. V4: portfolio allocation and multi-asset risk
6. V5: guarded continuous learning and champion/challenger promotion

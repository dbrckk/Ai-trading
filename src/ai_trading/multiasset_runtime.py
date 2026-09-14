from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from .audit import AuditLog
from .config import RiskConfig
from .multiasset_state import AssetPosition, MultiAssetStateStore
from .portfolio import AllocationConfig, inverse_volatility_weights, target_notionals
from .portfolio_risk import PortfolioRiskConfig, evaluate_portfolio_risk
from .runtime_lock import RuntimeLock


@dataclass(frozen=True)
class MultiAssetStepResult:
    processed: bool
    timestamp: str | None
    equity: float
    cash: float
    weights: dict[str, float]
    notionals: dict[str, float]
    risk_approved: bool
    risk_reasons: tuple[str, ...]


class MultiAssetPaperRuntime:
    def __init__(
        self,
        *,
        risk_config: RiskConfig | None = None,
        allocation_config: AllocationConfig | None = None,
        portfolio_risk_config: PortfolioRiskConfig | None = None,
        state_store: MultiAssetStateStore | None = None,
        audit_log: AuditLog | None = None,
        lock_path: str = "artifacts/multiasset_runtime.lock",
    ) -> None:
        self.risk_config = risk_config or RiskConfig()
        self.allocation_config = allocation_config or AllocationConfig()
        self.portfolio_risk_config = portfolio_risk_config or PortfolioRiskConfig()
        self.state_store = state_store or MultiAssetStateStore()
        self.audit = audit_log or AuditLog("artifacts/multiasset_audit.jsonl")
        self.lock_path = lock_path

    def step(self, markets: dict[str, pd.DataFrame]) -> MultiAssetStepResult:
        if len(markets) < 2:
            raise ValueError("Need at least two assets")

        with RuntimeLock(self.lock_path):
            closes = {}
            opens = {}
            execution_times: set[str] = set()

            for symbol, df in markets.items():
                if len(df) < 40:
                    raise ValueError(f"Insufficient data for {symbol}")
                closes[symbol] = df["Close"].astype(float)
                opens[symbol] = df["Open"].astype(float)
                execution_times.add(str(df.index[-1]))

            if len(execution_times) != 1:
                raise ValueError("Assets are not aligned on the same latest bar")
            execution_time = next(iter(execution_times))

            state = self.state_store.load(self.risk_config.starting_cash)
            if state.last_processed == execution_time:
                return MultiAssetStepResult(
                    processed=False,
                    timestamp=execution_time,
                    equity=state.equity(),
                    cash=state.cash,
                    weights={},
                    notionals={},
                    risk_approved=False,
                    risk_reasons=("bar already processed",),
                )

            close_frame = pd.DataFrame(closes).dropna()
            returns = close_frame.pct_change().dropna()
            if len(returns) < 20:
                raise ValueError("Insufficient aligned return history")

            weights = inverse_volatility_weights(returns, self.allocation_config)
            equity = state.equity()
            notionals = target_notionals(equity, weights)

            risk = evaluate_portfolio_risk(
                notionals,
                equity,
                returns,
                self.portfolio_risk_config,
            )

            if risk.approved:
                total_costs = 0.0
                for symbol in weights.index:
                    price = float(opens[symbol].iloc[-1])
                    position = state.positions.setdefault(symbol, AssetPosition())
                    desired_units = float(notionals[symbol]) / price
                    delta_units = desired_units - position.units
                    gross = abs(delta_units) * price
                    bps = self.risk_config.transaction_cost_bps + self.risk_config.slippage_bps
                    total_costs += gross * bps / 10_000.0
                    state.cash -= delta_units * price
                    position.units = desired_units
                    position.last_price = float(closes[symbol].iloc[-1])

                state.cash -= total_costs

            for symbol in weights.index:
                position = state.positions.setdefault(symbol, AssetPosition())
                position.last_price = float(closes[symbol].iloc[-1])

            state.processed_bars += 1
            state.last_processed = execution_time
            current_equity = state.equity()
            state.peak_equity = max(state.peak_equity, current_equity)
            self.state_store.save(state)

            self.audit.append(
                "multiasset_runtime_step",
                {
                    "timestamp": execution_time,
                    "weights": weights.to_dict(),
                    "notionals": notionals.to_dict(),
                    "risk_approved": risk.approved,
                    "risk_reasons": list(risk.reasons),
                    "equity": current_equity,
                    "cash": state.cash,
                },
            )

            return MultiAssetStepResult(
                processed=True,
                timestamp=execution_time,
                equity=current_equity,
                cash=state.cash,
                weights={k: float(v) for k, v in weights.items()},
                notionals={k: float(v) for k, v in notionals.items()},
                risk_approved=risk.approved,
                risk_reasons=risk.reasons,
            )

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from .backtest import WalkForwardBacktester, WalkForwardConfig
from .champions import ChampionRegistry
from .config import ModelConfig, RiskConfig
from .continuous import ContinuousCycleResult, run_learning_cycle
from .drift import detect_drift
from .features import make_features
from .governor_state_store import GovernorStateStore
from .guardrails import HealthDecision, evaluate_health
from .performance import PerformanceMetrics
from .regime_validation import RegimeValidation, validate_regime_returns
from .runtime import PaperAutonomousRuntime, RuntimeStepResult


@dataclass(frozen=True)
class OrchestrationResult:
    runtime: RuntimeStepResult
    health: HealthDecision | None
    regime_validation: RegimeValidation | None
    learning_cycle: ContinuousCycleResult | None
    learning_cycle_triggered: bool
    trigger_reason: str | None


class AutonomousPaperOrchestrator:
    def __init__(
        self,
        *,
        runtime: PaperAutonomousRuntime | None = None,
        registry: ChampionRegistry | None = None,
        learning_trials: int = 10,
        governor_state_store: GovernorStateStore | None = None,
    ) -> None:
        self.runtime = runtime or PaperAutonomousRuntime()
        self.registry = registry or ChampionRegistry()
        self.learning_trials = learning_trials
        self.governor_state_store = governor_state_store or GovernorStateStore()

    def _health_checks(
        self,
        df: pd.DataFrame,
    ) -> tuple[HealthDecision, RegimeValidation, PerformanceMetrics]:
        report = WalkForwardBacktester(
            risk_config=RiskConfig(),
            model_config=ModelConfig(),
            config=WalkForwardConfig(use_ensemble=True),
        ).run(df)

        features = make_features(df).dropna()
        feature_split = max(60, int(len(features) * 0.75))
        strategy_returns = report.equity_curve.pct_change().dropna()
        return_split = max(20, int(len(strategy_returns) * 0.75))

        drift = detect_drift(
            features.iloc[:feature_split],
            features.iloc[feature_split:],
            strategy_returns.iloc[:return_split],
            strategy_returns.iloc[return_split:],
        )
        return (
            evaluate_health(report.metrics, drift),
            validate_regime_returns(report.regime_returns),
            report.metrics,
        )

    def step(
        self,
        df: pd.DataFrame,
        *,
        symbol: str,
        run_health_check: bool = True,
    ) -> OrchestrationResult:
        runtime_result = self.runtime.step(df)

        health: HealthDecision | None = None
        regime_validation: RegimeValidation | None = None
        current_metrics: PerformanceMetrics | None = None

        if run_health_check and runtime_result.processed:
            health, regime_validation, current_metrics = self._health_checks(df)

        trigger_reason: str | None = None
        if runtime_result.retrain_due:
            trigger_reason = "scheduled learning interval reached"
        elif health is not None and health.rollback:
            trigger_reason = f"health degradation: {health.reason}"
        elif regime_validation is not None and not regime_validation.valid:
            trigger_reason = f"regime validation failed: {regime_validation.reason}"

        governor_state = self.governor_state_store.load()
        if trigger_reason is not None and governor_state.verdict != "TRADE":
            trigger_reason = (
                f"{trigger_reason}; learning blocked by governor "
                f"{governor_state.verdict}: {governor_state.reason}"
            )

        cycle: ContinuousCycleResult | None = None
        if trigger_reason is not None and governor_state.verdict == "TRADE":
            active = self.registry.active()
            if active is not None:
                champion_metrics = PerformanceMetrics(**active.metrics)
            elif current_metrics is not None:
                champion_metrics = current_metrics
            else:
                champion_metrics = self._health_checks(df)[2]

            cycle = run_learning_cycle(
                df,
                symbol=symbol,
                champion_metrics=champion_metrics,
                registry=self.registry,
                trials=self.learning_trials,
            )

            state = self.runtime.state_store.load(self.runtime.risk_config.starting_cash)
            state.last_learning_cycle_bar = state.processed_bars
            self.runtime.state_store.save(state)

            self.runtime.audit.append(
                "learning_cycle",
                {
                    "trigger_reason": trigger_reason,
                    "promoted": cycle.promoted,
                    "champion_version": cycle.champion_version,
                    "promotion_reason": cycle.promotion.reason,
                    "regime_validation": cycle.regime_validation.reason,
                    "bootstrap_probability_positive": cycle.robustness.probability_positive,
                    "bootstrap_p05_return": cycle.robustness.p05_return,
                },
            )

        return OrchestrationResult(
            runtime=runtime_result,
            health=health,
            regime_validation=regime_validation,
            learning_cycle=cycle,
            learning_cycle_triggered=cycle is not None,
            trigger_reason=trigger_reason,
        )

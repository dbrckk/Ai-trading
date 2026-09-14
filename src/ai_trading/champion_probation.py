from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

from .champions import ChampionRecord, ChampionRegistry
from .lifecycle_log import LifecycleEventLog
from .model_quarantine import ModelQuarantineStore


@dataclass(frozen=True)
class ProbationPolicy:
    min_observations: int = 5
    max_sharpe_drop: float = 0.30
    max_sortino_drop: float = 0.40
    max_calmar_drop: float = 0.30
    max_drawdown_increase: float = 0.03
    hard_max_drawdown_increase: float = 0.07


@dataclass(frozen=True)
class ProbationState:
    version: str
    baseline_metrics: dict[str, float]
    observations: int = 0
    status: str = "probation"
    failure_count: int = 0


@dataclass(frozen=True)
class ProbationResult:
    action: str
    reasons: tuple[str, ...]
    state: ProbationState
    active_champion: ChampionRecord | None


class ChampionProbationStore:
    def __init__(self, path: str | Path = "artifacts/champion_probation.json") -> None:
        self.path = Path(path)

    def load(self) -> ProbationState | None:
        if not self.path.exists():
            return None
        return ProbationState(**json.loads(self.path.read_text(encoding="utf-8")))

    def save(self, state: ProbationState) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temp = self.path.with_suffix(".tmp")
        temp.write_text(json.dumps(asdict(state), sort_keys=True), encoding="utf-8")
        temp.replace(self.path)


class ChampionProbationManager:
    def __init__(
        self,
        registry: ChampionRegistry,
        *,
        store: ChampionProbationStore | None = None,
        policy: ProbationPolicy | None = None,
        quarantine_store: ModelQuarantineStore | None = None,
        lifecycle_log: LifecycleEventLog | None = None,
    ) -> None:
        self.registry = registry
        self.store = store or ChampionProbationStore()
        self.policy = policy or ProbationPolicy()
        self.quarantine_store = quarantine_store or ModelQuarantineStore()
        self.lifecycle_log = lifecycle_log or LifecycleEventLog()

    def start(self, champion: ChampionRecord) -> ProbationState:
        state = ProbationState(
            version=champion.version,
            baseline_metrics=dict(champion.metrics),
        )
        self.store.save(state)
        return state

    def observe(
        self,
        metrics: dict[str, float],
        *,
        processed_bar: int = 0,
    ) -> ProbationResult:
        state = self.store.load()
        active = self.registry.active()
        if state is None:
            raise RuntimeError("No champion probation is active")
        if active is None or active.version != state.version:
            raise RuntimeError("Probation champion does not match active champion")

        required = ("sharpe", "sortino", "max_drawdown", "calmar")
        missing = [
            name
            for name in required
            if name not in state.baseline_metrics or name not in metrics
        ]
        if missing:
            reasons = (f"missing probation metrics: {', '.join(sorted(missing))}",)
            return self._rollback(state, reasons, processed_bar=processed_bar)

        observations = state.observations + 1
        baseline = state.baseline_metrics
        drawdown_increase = float(metrics["max_drawdown"] - baseline["max_drawdown"])
        sharpe_drop = float(baseline["sharpe"] - metrics["sharpe"])
        sortino_drop = float(baseline["sortino"] - metrics["sortino"])
        calmar_drop = float(baseline["calmar"] - metrics["calmar"])

        reasons: list[str] = []
        if drawdown_increase > self.policy.hard_max_drawdown_increase:
            reasons.append("hard drawdown probation limit breached")
        elif observations >= self.policy.min_observations:
            if drawdown_increase > self.policy.max_drawdown_increase:
                reasons.append("drawdown degraded during probation")
            if sharpe_drop > self.policy.max_sharpe_drop:
                reasons.append("Sharpe degraded during probation")
            if sortino_drop > self.policy.max_sortino_drop:
                reasons.append("Sortino degraded during probation")
            if calmar_drop > self.policy.max_calmar_drop:
                reasons.append("Calmar degraded during probation")

        updated = ProbationState(
            version=state.version,
            baseline_metrics=state.baseline_metrics,
            observations=observations,
            status="probation",
            failure_count=state.failure_count,
        )
        self.store.save(updated)

        if reasons:
            return self._rollback(
                updated,
                tuple(reasons),
                processed_bar=processed_bar,
            )

        if observations >= self.policy.min_observations:
            passed = ProbationState(
                version=updated.version,
                baseline_metrics=updated.baseline_metrics,
                observations=updated.observations,
                status="passed",
                failure_count=updated.failure_count,
            )
            self.store.save(passed)
            self.quarantine_store.record_success(passed.version)
            self.lifecycle_log.append(
                event="probation_passed",
                version=passed.version,
                model_name=active.model_name,
                processed_bar=processed_bar,
            )
            return ProbationResult("pass", (), passed, active)

        return ProbationResult("continue", (), updated, active)

    def _rollback(
        self,
        state: ProbationState,
        reasons: tuple[str, ...],
        *,
        processed_bar: int,
    ) -> ProbationResult:
        rolled_back = self.registry.rollback()
        failed = ProbationState(
            version=state.version,
            baseline_metrics=state.baseline_metrics,
            observations=state.observations,
            status="rolled_back",
            failure_count=state.failure_count + 1,
        )
        self.store.save(failed)
        self.quarantine_store.record_failure(
            failed.version,
            processed_bar=processed_bar,
            reason="; ".join(reasons),
            failure_type="performance_failure",
        )
        self.lifecycle_log.append(
            event="rollback",
            version=failed.version,
            model_name="",
            reason="; ".join(reasons),
            failure_type="performance_failure",
            processed_bar=processed_bar,
            metadata={"rolled_back_to": rolled_back.version},
        )
        return ProbationResult("rollback", reasons, failed, rolled_back)

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

import pandas as pd

from .data import load_history
from .persistence import PaperPersistence, PersistedRuntime, build_runtime_key
from .runtime import PaperAutonomousRuntime
from .shadow_challenger import evaluate_shadow_challenger

DEFAULT_MAX_CATCHUP_BARS = 72


@dataclass(frozen=True)
class PaperCycleResult:
    processed: int
    remaining_backlog: bool
    last_processed: str | None
    processed_bars: int
    reason: str


class PaperCycleRunner:
    """Run a bounded one-shot paper cycle against durable runtime state."""

    def __init__(
        self,
        *,
        persistence: PaperPersistence,
        data_loader: Callable[[str, str, str], pd.DataFrame] = load_history,
        runtime_factory: Callable[..., PaperAutonomousRuntime] = PaperAutonomousRuntime,
    ) -> None:
        self.persistence = persistence
        self.data_loader = data_loader
        self.runtime_factory = runtime_factory

    @staticmethod
    def _is_logically_fresh(snapshot: PersistedRuntime) -> bool:
        state = snapshot.state
        return snapshot.is_new or (
            snapshot.revision == 0
            and snapshot.model is None
            and state.last_processed is None
            and state.processed_bars == 0
            and state.last_learning_cycle_bar == 0
            and state.units == 0.0
            and state.last_price == 0.0
        )

    @classmethod
    def _pending_targets(
        cls,
        snapshot: PersistedRuntime,
        eligible: tuple[object, ...],
    ) -> list[object]:
        if cls._is_logically_fresh(snapshot):
            return list(eligible[-1:])

        last_processed = snapshot.state.last_processed
        if last_processed is None:
            raise RuntimeError("persisted runtime is missing last_processed")

        positions = {str(value): index for index, value in enumerate(eligible)}
        position = positions.get(last_processed)
        if position is None:
            raise RuntimeError("persisted last_processed is outside loaded history")
        return list(eligible[position + 1 :])

    def run_once(
        self,
        *,
        symbol: str,
        period: str,
        interval: str,
        max_catchup_bars: int = DEFAULT_MAX_CATCHUP_BARS,
        shadow_challenger_enabled: bool = False,
    ) -> PaperCycleResult:
        if max_catchup_bars < 1:
            raise ValueError("max_catchup_bars must be at least 1")

        runtime_key = build_runtime_key(symbol, interval)
        runtime = self.runtime_factory(
            symbol=symbol,
            persistence=self.persistence,
            runtime_key=runtime_key,
        )
        market = self.data_loader(symbol, period, interval)
        prepared = runtime.prepare_market(market)
        eligible = prepared.eligible
        if not eligible:
            raise RuntimeError("market history contains no eligible execution bar")

        snapshot = self.persistence.load_runtime(
            runtime_key,
            runtime.risk_config.starting_cash,
        )
        pending = self._pending_targets(snapshot, eligible)
        if not pending:
            return PaperCycleResult(
                processed=0,
                remaining_backlog=False,
                last_processed=snapshot.state.last_processed,
                processed_bars=snapshot.state.processed_bars,
                reason="no new eligible bar",
            )

        shadow_result = None
        shadow_target: str | None = None
        if shadow_challenger_enabled:
            try:
                shadow_target = str(pending[0])
                shadow_result = evaluate_shadow_challenger(
                    market,
                    prepared.features,
                    prepared.labels,
                    pending[0],
                    horizon_bars=runtime.model_config.horizon_bars,
                )
            except Exception:  # noqa: BLE001 - observer must never disrupt execution
                shadow_result = None
                shadow_target = None

        processed = 0
        attempts = 0
        while pending and attempts < max_catchup_bars:
            target = pending[0]
            if shadow_result is not None and str(target) == shadow_target:
                result = runtime.step_prepared(
                    prepared,
                    target,
                    shadow_challenger=shadow_result,
                )
            else:
                result = runtime.step_prepared(prepared, target)
            attempts += 1
            if result.processed:
                processed += 1
            elif result.reason not in {
                "persistence revision conflict",
                "bar already processed",
            }:
                raise RuntimeError(f"paper cycle did not process target: {result.reason}")

            snapshot = self.persistence.load_runtime(
                runtime_key,
                runtime.risk_config.starting_cash,
            )
            pending = self._pending_targets(snapshot, eligible)

        remaining_backlog = bool(pending)
        if remaining_backlog:
            reason = "catch-up pending"
        elif processed:
            reason = f"processed {processed} bar(s)"
        else:
            reason = "concurrent progress observed"

        return PaperCycleResult(
            processed=processed,
            remaining_backlog=remaining_backlog,
            last_processed=snapshot.state.last_processed,
            processed_bars=snapshot.state.processed_bars,
            reason=reason,
        )

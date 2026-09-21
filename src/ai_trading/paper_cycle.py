from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

import pandas as pd

from .data import load_history
from .features import make_features
from .mtf_shadow_challenger import (
    evaluate_multi_timeframe_shadow,
    select_observable_execution_target,
)
from .mtf_shadow_config import validated_mtf_shadow_config
from .persistence import PaperPersistence, PersistedRuntime, build_runtime_key
from .runtime import PaperAutonomousRuntime
from .shadow_challenger import evaluate_shadow_challenger

DEFAULT_MAX_CATCHUP_BARS = 72
_MAX_PROVIDER_GAP_RESUME = pd.Timedelta(days=3)


def _utc_timestamp(value: object) -> pd.Timestamp:
    timestamp = pd.Timestamp(value)
    if timestamp.tzinfo is None:
        return timestamp.tz_localize("UTC")
    return timestamp.tz_convert("UTC")


def _is_mtf_evaluation_boundary(
    execution_idx: object,
    interval: str,
    horizon_minutes: int = 15,
) -> bool:
    if interval != "5m":
        return False
    if horizon_minutes < 5 or horizon_minutes % 5 != 0:
        raise ValueError("horizon_minutes must be a positive 5-minute multiple")
    timestamp = pd.Timestamp(execution_idx)
    epoch_minutes = timestamp.value // (60 * 1_000_000_000)
    return epoch_minutes % horizon_minutes == 0



@dataclass(frozen=True)
class PaperCycleResult:
    processed: int
    remaining_backlog: bool
    last_processed: str | None
    processed_bars: int
    reason: str
    mtf_evaluated: bool = False


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
        market_index: pd.Index | None = None,
    ) -> list[object]:
        if cls._is_logically_fresh(snapshot):
            return list(eligible[-1:])

        last_processed = snapshot.state.last_processed
        if last_processed is None:
            raise RuntimeError("persisted runtime is missing last_processed")

        positions = {str(value): index for index, value in enumerate(eligible)}
        position = positions.get(last_processed)
        if position is not None:
            return list(eligible[position + 1 :])

        if market_index is None:
            raise RuntimeError("persisted last_processed is outside loaded history")

        market_positions = {
            str(value): index
            for index, value in enumerate(market_index)
        }
        market_position = market_positions.get(last_processed)
        if market_position is not None:
            return [
                target
                for target in eligible
                if market_positions.get(str(target), -1) > market_position
            ]

        try:
            persisted_time = _utc_timestamp(last_processed)
            raw_times = tuple(_utc_timestamp(value) for value in market_index)
            eligible_times = tuple(_utc_timestamp(value) for value in eligible)
        except (TypeError, ValueError):
            raise RuntimeError(
                "persisted last_processed is outside loaded history"
            ) from None

        if not raw_times:
            raise RuntimeError("persisted last_processed is outside loaded history")

        first_raw = raw_times[0]
        last_raw = raw_times[-1]
        if persisted_time < first_raw:
            if first_raw - persisted_time > _MAX_PROVIDER_GAP_RESUME:
                raise RuntimeError(
                    "persisted last_processed is outside loaded history"
                )
        elif persisted_time > last_raw:
            if persisted_time - last_raw > _MAX_PROVIDER_GAP_RESUME:
                raise RuntimeError(
                    "persisted last_processed is outside loaded history"
                )
            return []

        return [
            target
            for target, target_time in zip(eligible, eligible_times, strict=True)
            if target_time > persisted_time
        ]

    def run_once(
        self,
        *,
        symbol: str,
        period: str,
        interval: str,
        max_catchup_bars: int = DEFAULT_MAX_CATCHUP_BARS,
        shadow_challenger_enabled: bool = False,
        mtf_period: str | None = None,
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
        pending = self._pending_targets(snapshot, eligible, market.index)
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
        mtf_shadow_result = None
        mtf_attach_target: str | None = None
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

            mtf_config = validated_mtf_shadow_config(symbol)
            mtf_candidate = (
                next(
                    (
                        target
                        for target in pending[:max_catchup_bars]
                        if _is_mtf_evaluation_boundary(
                            target,
                            interval,
                            mtf_config.horizon_minutes,
                        )
                    ),
                    None,
                )
                if mtf_config is not None
                else None
            )
            if mtf_candidate is not None and mtf_config is not None:
                try:
                    mtf_market = (
                        market
                        if not mtf_period or mtf_period == period
                        else self.data_loader(symbol, mtf_period, interval)
                    )
                    mtf_current = {
                        str(index): index
                        for index in mtf_market.index
                    }.get(str(mtf_candidate))
                    if mtf_current is not None:
                        mtf_execution = select_observable_execution_target(
                            mtf_market,
                            tuple(mtf_market.index[1:]),
                            mtf_current,
                            horizon_bars=mtf_config.horizon_bars,
                        )
                        if mtf_execution is not None:
                            mtf_shadow_result = evaluate_multi_timeframe_shadow(
                                mtf_market,
                                make_features(mtf_market),
                                mtf_execution,
                                horizon_bars=mtf_config.horizon_bars,
                                min_train_rows=mtf_config.min_train_rows,
                                max_train_rows=mtf_config.max_train_rows,
                                feature_warmup_rows=mtf_config.feature_warmup_rows,
                                minimum_threshold=mtf_config.minimum_threshold,
                                atr_multiplier=mtf_config.atr_multiplier,
                                min_confidence=mtf_config.min_confidence,
                                config_name=mtf_config.config_name,
                            )
                            if mtf_shadow_result is not None:
                                mtf_attach_target = str(mtf_candidate)
                except Exception:  # noqa: BLE001 - observer must never disrupt execution
                    mtf_shadow_result = None
                    mtf_attach_target = None

        processed = 0
        attempts = 0
        while pending and attempts < max_catchup_bars:
            target = pending[0]
            observer_kwargs = {}
            if shadow_result is not None and str(target) == shadow_target:
                observer_kwargs["shadow_challenger"] = shadow_result
            if mtf_shadow_result is not None and str(target) == mtf_attach_target:
                observer_kwargs["mtf_shadow_challenger"] = mtf_shadow_result
            result = runtime.step_prepared(
                prepared,
                target,
                **observer_kwargs,
            )
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
            pending = self._pending_targets(snapshot, eligible, market.index)

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
            mtf_evaluated=mtf_shadow_result is not None,
        )

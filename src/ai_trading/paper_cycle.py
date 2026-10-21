from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime

import pandas as pd

from .data import load_history
from .data_quality import evaluate_market_data_quality
from .features import make_features
from .mtf_shadow_challenger import (
    evaluate_multi_timeframe_shadow,
    select_observable_execution_target,
)
from .mtf_shadow_config import validated_mtf_shadow_config
from .persistence import PaperPersistence, PersistedRuntime, build_runtime_key
from .river_v2_shadow import observe_river_v2_forward, river_v2_observer_enabled
from .runtime import PaperAutonomousRuntime
from .shadow_challenger import evaluate_shadow_challenger

DEFAULT_MAX_CATCHUP_BARS = 72
_MAX_PROVIDER_GAP_RESUME = pd.Timedelta(days=3)
_FIVE_MINUTES = pd.Timedelta(minutes=5)
_CANDLE_FINALITY_BUFFER = pd.Timedelta(seconds=2)


def _utc_now() -> pd.Timestamp:
    return pd.Timestamp(datetime.now(UTC))


def _completed_market_bars(
    market: pd.DataFrame,
    *,
    interval: str,
    now: pd.Timestamp | None = None,
) -> pd.DataFrame:
    """Exclude provider candles that have not finished before paper execution.

    Yahoo's intraday response can contain an OHLC row whose timestamp is the
    *start* of the currently forming candle. Executing its partial close would
    permanently persist a decision against a price that later changes.
    Date-only and historical non-5m pipelines keep their prior behaviour.
    Naive timestamps are interpreted as UTC, as in the existing paper runner.
    """
    if interval != "5m":
        return market
    if not isinstance(market.index, pd.DatetimeIndex) or market.index.hasnans:
        raise ValueError("5m paper market requires valid datetime timestamps")
    current = _utc_now() if now is None else pd.Timestamp(now)
    if current.tzinfo is None:
        raise ValueError("observation time must be timezone-aware")
    current = current.tz_convert("UTC")
    timestamps = (
        market.index.tz_localize("UTC")
        if market.index.tz is None
        else market.index.tz_convert("UTC")
    )
    completed = timestamps + _FIVE_MINUTES + _CANDLE_FINALITY_BUFFER <= current
    return market.iloc[completed]


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
    partial_failure: bool = False
    failed_markets: int = 0
    side: int = 0
    confidence: float = 0.0
    approved: bool = False
    decision_reason: str | None = None


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
        market = _completed_market_bars(
            self.data_loader(symbol, period, interval),
            interval=interval,
        )
        quality = evaluate_market_data_quality(market)
        if not quality.valid:
            reasons = ",".join(quality.reasons) or "score below threshold"
            raise RuntimeError(f"market data failed quality gate: {reasons}")
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
                    mtf_quality = evaluate_market_data_quality(mtf_market)
                    if not mtf_quality.valid:
                        raise RuntimeError("MTF market data failed quality gate")
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
        last_decision = None
        while pending and attempts < max_catchup_bars:
            target = pending[0]
            observer_kwargs = {}
            if shadow_result is not None and str(target) == shadow_target:
                observer_kwargs["shadow_challenger"] = shadow_result
            if mtf_shadow_result is not None and str(target) == mtf_attach_target:
                observer_kwargs["mtf_shadow_challenger"] = mtf_shadow_result
            if (
                shadow_challenger_enabled
                and river_v2_observer_enabled()
                and interval == "5m"
                and str(target) == str(eligible[-1])
            ):
                try:
                    river_v2 = observe_river_v2_forward(
                        market,
                        horizon_bars=runtime.model_config.horizon_bars,
                        return_threshold=runtime.model_config.return_threshold,
                        min_confidence=runtime.risk_config.min_confidence,
                    )
                    if river_v2 is not None:
                        observer_kwargs["river_v2_shadow"] = river_v2
                except Exception:  # noqa: BLE001 - research observer cannot stop paper trades
                    observer_kwargs.pop("river_v2_shadow", None)
            result = runtime.step_prepared(
                prepared,
                target,
                **observer_kwargs,
            )
            attempts += 1
            if result.processed:
                processed += 1
                last_decision = result
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
            side=last_decision.side if last_decision is not None else 0,
            confidence=last_decision.confidence if last_decision is not None else 0.0,
            approved=last_decision.approved if last_decision is not None else False,
            decision_reason=last_decision.reason if last_decision is not None else None,
        )

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from time import perf_counter

from .config import RiskConfig
from .paper_cycle import DEFAULT_MAX_CATCHUP_BARS, PaperCycleResult, PaperCycleRunner
from .persistence import PaperPersistence, build_runtime_key
from .persistence_factory import build_paper_persistence
from .runtime_status import HostedRuntimeStatus


@dataclass(frozen=True)
class ProductionPaperCycleSettings:
    symbol: str = "GC=F"
    period: str = "5d"
    interval: str = "5m"
    max_catchup_bars: int = DEFAULT_MAX_CATCHUP_BARS
    poll_seconds: float = 300.0
    shadow_challenger_enabled: bool = False
    mtf_period: str = "1mo"


class PaperCycleServiceError(RuntimeError):
    def __init__(self, *, code: str, error_type: str) -> None:
        super().__init__(code)
        self.code = code
        self.error_type = error_type


def _now_utc() -> str:
    return datetime.now(UTC).isoformat()


def _default_runner_factory(persistence: PaperPersistence) -> PaperCycleRunner:
    return PaperCycleRunner(persistence=persistence)


_SAFE_RUNTIME_FAILURES = {
    "persisted last_processed is outside loaded history": (
        "persisted_bar_outside_loaded_history"
    ),
    "persisted runtime is missing last_processed": (
        "persisted_runtime_missing_last_processed"
    ),
    "market history contains no eligible execution bar": (
        "no_eligible_market_bar"
    ),
}


def _safe_failure_detail(exc: Exception) -> str:
    if isinstance(exc, RuntimeError):
        message = str(exc)
        code = _SAFE_RUNTIME_FAILURES.get(message)
        if code is not None:
            return f"RuntimeError: {code}"
        if message.startswith("paper cycle did not process target:"):
            return "RuntimeError: target_processing_failed"
        if message.startswith("market data failed quality gate:"):
            return "RuntimeError: market_data_quality_failed"
    return f"{type(exc).__name__}: worker failure"


def _can_reuse_last_paper_decision(
    previous: HostedRuntimeStatus | None,
    result: PaperCycleResult,
    *,
    symbol: str,
    interval: str,
    processed_bars: int,
) -> bool:
    """Reuse a completed decision only when the durable runtime has not advanced.

    The dashboard independently checks session state, heartbeat and bar age
    before exposing this decision; a past decision never becomes a new trade.
    """
    return (
        previous is not None
        and previous.engine_status == "RUNNING"
        and previous.error is None
        and previous.processed
        and previous.reason != "catch-up pending"
        and previous.symbol == symbol
        and previous.interval == interval
        and previous.last_cycle_timestamp is not None
        and previous.last_cycle_timestamp == result.last_processed
        and previous.processed_bars == processed_bars
        and result.processed_bars == processed_bars
        and result.processed == 0
        and result.reason == "no new eligible bar"
        and not result.remaining_backlog
    )


def run_production_paper_cycle(
    settings: ProductionPaperCycleSettings,
    *,
    persistence: PaperPersistence | None = None,
    persistence_factory: Callable[[], PaperPersistence] = build_paper_persistence,
    runner_factory: Callable[[PaperPersistence], PaperCycleRunner] = _default_runner_factory,
) -> PaperCycleResult:
    if settings.max_catchup_bars < 1:
        raise ValueError("max_catchup_bars must be at least 1")

    runtime_key = build_runtime_key(settings.symbol, settings.interval)
    starting_cash = RiskConfig().starting_cash
    cycle_started = perf_counter()

    backend = persistence
    if backend is None:
        try:
            backend = persistence_factory()
        except Exception as exc:  # noqa: BLE001 - sanitize provider errors here
            raise PaperCycleServiceError(
                code="storage_unavailable",
                error_type=type(exc).__name__,
            ) from None

    try:
        previous_status = backend.load_runtime_status(runtime_key)
        previous_cycle_errors = (
            previous_status.consecutive_cycle_errors
            if previous_status is not None
            else 0
        )
        backend.save_runtime_status(
            runtime_key,
            HostedRuntimeStatus(
                engine_status="STARTING",
                symbol=settings.symbol,
                interval=settings.interval,
                updated_at_utc=_now_utc(),
                equity=(
                    previous_status.equity
                    if previous_status is not None and previous_status.equity > 0
                    else starting_cash
                ),
                units=previous_status.units if previous_status is not None else 0.0,
                processed_bars=(
                    previous_status.processed_bars
                    if previous_status is not None else 0
                ),
                poll_seconds=settings.poll_seconds,
                consecutive_cycle_errors=previous_cycle_errors,
            ),
        )
    except Exception as exc:  # noqa: BLE001 - storage boundary is fail-closed
        raise PaperCycleServiceError(
            code="storage_unavailable",
            error_type=type(exc).__name__,
        ) from None

    try:
        runner = runner_factory(backend)
        if settings.shadow_challenger_enabled:
            result = runner.run_once(
                symbol=settings.symbol,
                period=settings.period,
                interval=settings.interval,
                max_catchup_bars=settings.max_catchup_bars,
                shadow_challenger_enabled=True,
                mtf_period=settings.mtf_period,
            )
        else:
            result = runner.run_once(
                symbol=settings.symbol,
                period=settings.period,
                interval=settings.interval,
                max_catchup_bars=settings.max_catchup_bars,
            )
        state = backend.load_runtime(runtime_key, starting_cash).state
        equity = state.cash + state.units * state.last_price
        cycle_duration_seconds = perf_counter() - cycle_started
        reuse_decision = _can_reuse_last_paper_decision(
            previous_status,
            result,
            symbol=settings.symbol,
            interval=settings.interval,
            processed_bars=state.processed_bars,
        )
        last_decision = previous_status if reuse_decision else None
        backend.save_runtime_status(
            runtime_key,
            HostedRuntimeStatus(
                engine_status="RUNNING",
                symbol=settings.symbol,
                interval=settings.interval,
                updated_at_utc=_now_utc(),
                last_cycle_timestamp=result.last_processed,
                # A no-op poll must not erase a still-current paper decision.
                # "reason" still describes this poll; time/approval stay unchanged.
                processed=result.processed > 0 or reuse_decision,
                side=(
                    result.side if result.processed
                    else last_decision.side if last_decision is not None else 0
                ),
                confidence=(
                    result.confidence if result.processed
                    else last_decision.confidence if last_decision is not None else 0.0
                ),
                approved=(
                    result.approved if result.processed
                    else last_decision.approved if last_decision is not None else False
                ),
                reason=result.reason,
                decision_reason=(
                    result.decision_reason if result.processed
                    else last_decision.decision_reason
                    if last_decision is not None else None
                ),
                equity=equity,
                units=state.units,
                processed_bars=state.processed_bars,
                poll_seconds=settings.poll_seconds,
                consecutive_cycle_errors=0,
                cycle_duration_seconds=cycle_duration_seconds,
                mtf_evaluated=result.mtf_evaluated,
            ),
        )
        return result
    except Exception as exc:  # noqa: BLE001 - sanitize execution/provider failures
        try:
            backend.save_runtime_status(
                runtime_key,
                HostedRuntimeStatus(
                    engine_status="ERROR",
                    symbol=settings.symbol,
                    interval=settings.interval,
                    updated_at_utc=_now_utc(),
                    error=_safe_failure_detail(exc),
                    poll_seconds=settings.poll_seconds,
                    consecutive_cycle_errors=previous_cycle_errors + 1,
                    cycle_duration_seconds=perf_counter() - cycle_started,
                ),
            )
        except Exception:  # noqa: BLE001, S110 - best-effort failure reporting
            pass
        raise PaperCycleServiceError(
            code="execution_failed",
            error_type=type(exc).__name__,
        ) from None

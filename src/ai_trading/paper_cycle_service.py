from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime

from .config import RiskConfig
from .paper_cycle import PaperCycleResult, PaperCycleRunner
from .persistence import PaperPersistence, build_runtime_key
from .persistence_factory import build_paper_persistence
from .runtime_status import HostedRuntimeStatus


@dataclass(frozen=True)
class ProductionPaperCycleSettings:
    symbol: str = "GC=F"
    period: str = "5d"
    interval: str = "5m"
    max_catchup_bars: int = 12
    poll_seconds: float = 300.0


class PaperCycleServiceError(RuntimeError):
    def __init__(self, *, code: str, error_type: str) -> None:
        super().__init__(code)
        self.code = code
        self.error_type = error_type


def _now_utc() -> str:
    return datetime.now(UTC).isoformat()


def _default_runner_factory(persistence: PaperPersistence) -> PaperCycleRunner:
    return PaperCycleRunner(persistence=persistence)


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
        backend.save_runtime_status(
            runtime_key,
            HostedRuntimeStatus(
                engine_status="STARTING",
                symbol=settings.symbol,
                interval=settings.interval,
                updated_at_utc=_now_utc(),
                equity=starting_cash,
                poll_seconds=settings.poll_seconds,
            ),
        )
    except Exception as exc:  # noqa: BLE001 - storage boundary is fail-closed
        raise PaperCycleServiceError(
            code="storage_unavailable",
            error_type=type(exc).__name__,
        ) from None

    try:
        result = runner_factory(backend).run_once(
            symbol=settings.symbol,
            period=settings.period,
            interval=settings.interval,
            max_catchup_bars=settings.max_catchup_bars,
        )
        state = backend.load_runtime(runtime_key, starting_cash).state
        equity = state.cash + state.units * state.last_price
        backend.save_runtime_status(
            runtime_key,
            HostedRuntimeStatus(
                engine_status="RUNNING",
                symbol=settings.symbol,
                interval=settings.interval,
                updated_at_utc=_now_utc(),
                last_cycle_timestamp=result.last_processed,
                processed=result.processed > 0,
                reason=result.reason,
                equity=equity,
                units=state.units,
                processed_bars=state.processed_bars,
                poll_seconds=settings.poll_seconds,
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
                    error=f"{type(exc).__name__}: worker failure",
                    poll_seconds=settings.poll_seconds,
                ),
            )
        except Exception:  # noqa: BLE001, S110 - best-effort failure reporting
            pass
        raise PaperCycleServiceError(
            code="execution_failed",
            error_type=type(exc).__name__,
        ) from None

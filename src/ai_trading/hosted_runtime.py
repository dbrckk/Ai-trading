from __future__ import annotations

import os
from collections.abc import Callable
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from threading import Thread

from .data import load_history
from .orchestrator import AutonomousPaperOrchestrator, OrchestrationResult
from .runtime import PaperAutonomousRuntime
from .runtime_status import HostedRuntimeStatus, HostedRuntimeStatusStore
from .scheduler import PaperScheduler, SchedulerConfig


@dataclass(frozen=True)
class HostedPaperSettings:
    enabled: bool = False
    symbol: str = "GC=F"
    period: str = "1y"
    interval: str = "1d"
    poll_seconds: float = 60.0

    @classmethod
    def from_env(cls) -> HostedPaperSettings:
        enabled = os.getenv("AI_TRADING_HOSTED_PAPER", "0").strip().lower() in {
            "1",
            "true",
            "yes",
            "on",
        }
        symbol = os.getenv("AI_TRADING_HOSTED_SYMBOL", "GC=F").strip() or "GC=F"
        period = os.getenv("AI_TRADING_HOSTED_PERIOD", "1y").strip() or "1y"
        interval = os.getenv("AI_TRADING_HOSTED_INTERVAL", "1d").strip() or "1d"
        poll_seconds = float(os.getenv("AI_TRADING_HOSTED_POLL_SECONDS", "60"))
        if poll_seconds < 0:
            raise ValueError("AI_TRADING_HOSTED_POLL_SECONDS must be >= 0")
        return cls(
            enabled=enabled,
            symbol=symbol,
            period=period,
            interval=interval,
            poll_seconds=poll_seconds,
        )


def _now_utc() -> str:
    return datetime.now(UTC).isoformat()


def run_hosted_paper_loop(settings: HostedPaperSettings) -> None:
    print(
        "Hosted paper worker: boot "
        f"symbol={settings.symbol} interval={settings.interval} ",
        f"period={settings.period} poll={settings.poll_seconds:g}s",
        flush=True,
    )
    runtime = PaperAutonomousRuntime(symbol=settings.symbol)
    status_store = HostedRuntimeStatusStore()
    status_store.save(
        HostedRuntimeStatus(
            engine_status="STARTING",
            symbol=settings.symbol,
            interval=settings.interval,
            updated_at_utc=_now_utc(),
            equity=runtime.risk_config.starting_cash,
        )
    )
    print("Hosted paper worker: STARTING status persisted", flush=True)
    orchestrator = AutonomousPaperOrchestrator(runtime=runtime)

    def report_iteration(result: OrchestrationResult) -> None:
        step = result.runtime
        status_store.save(
            HostedRuntimeStatus(
                engine_status="RUNNING",
                symbol=settings.symbol,
                interval=settings.interval,
                updated_at_utc=_now_utc(),
                last_cycle_timestamp=step.timestamp,
                processed=step.processed,
                side=step.side,
                confidence=step.confidence,
                approved=step.approved,
                reason=step.reason,
                equity=step.equity,
                units=step.units,
                processed_bars=step.processed_bars,
            )
        )
        print(
            "Hosted paper worker: cycle complete "
            f"processed={step.processed} side={step.side} "
            f"confidence={step.confidence:.3f} approved={step.approved}",
            flush=True,
        )

    scheduler = PaperScheduler(
        orchestrator=orchestrator,
        data_loader=lambda: load_history(
            settings.symbol,
            settings.period,
            settings.interval,
        ),
        symbol=settings.symbol,
        config=SchedulerConfig(
            poll_seconds=settings.poll_seconds,
            max_iterations=None,
        ),
        on_iteration=report_iteration,
    )
    print("Hosted paper worker: entering scheduler loop", flush=True)
    try:
        scheduler.run()
    except Exception as exc:
        current = status_store.load() or HostedRuntimeStatus(
            engine_status="STARTING",
            symbol=settings.symbol,
            interval=settings.interval,
            updated_at_utc=_now_utc(),
        )
        status_store.save(
            replace(
                current,
                engine_status="ERROR",
                updated_at_utc=_now_utc(),
                error=repr(exc),
            )
        )
        print(f"Hosted paper worker: ERROR {exc!r}", flush=True)
        raise


def start_hosted_paper_runtime(
    *,
    runner: Callable[[HostedPaperSettings], None] = run_hosted_paper_loop,
) -> Thread | None:
    settings = HostedPaperSettings.from_env()
    if not settings.enabled:
        print("Hosted paper worker: disabled", flush=True)
        return None

    print("Hosted paper worker: starting daemon thread", flush=True)
    thread = Thread(
        target=runner,
        args=(settings,),
        name="ai-trading-hosted-paper",
        daemon=True,
    )
    thread.start()
    print("Hosted paper worker: daemon thread started", flush=True)
    return thread

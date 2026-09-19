from __future__ import annotations

import os
from collections.abc import Callable
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from threading import Thread

from .data import load_history
from .orchestrator import AutonomousPaperOrchestrator, OrchestrationResult
from .persistence import PaperPersistence, build_runtime_key
from .persistence_factory import build_paper_persistence
from .runtime import PaperAutonomousRuntime
from .runtime_status import HostedRuntimeStatus
from .scheduler import PaperScheduler, SchedulerConfig


@dataclass(frozen=True)
class HostedPaperSettings:
    enabled: bool = False
    external_scheduler: bool = False
    symbol: str = "GC=F"
    period: str = "1y"
    interval: str = "1d"
    poll_seconds: float = 60.0
    shadow_challenger: bool = False
    symbols: tuple[str, ...] = ()

    @property
    def runtime_key(self) -> str:
        return build_runtime_key(self.symbol, self.interval)

    @property
    def market_symbols(self) -> tuple[str, ...]:
        return self.symbols or (self.symbol,)

    @classmethod
    def from_env(cls) -> HostedPaperSettings:
        enabled = os.getenv("AI_TRADING_HOSTED_PAPER", "0").strip().lower() in {
            "1",
            "true",
            "yes",
            "on",
        }
        external_scheduler = os.getenv(
            "AI_TRADING_EXTERNAL_SCHEDULER",
            "0",
        ).strip().lower() in {
            "1",
            "true",
            "yes",
            "on",
        }
        symbol = os.getenv("AI_TRADING_HOSTED_SYMBOL", "GC=F").strip() or "GC=F"
        raw_symbols = os.getenv("AI_TRADING_HOSTED_SYMBOLS", "").strip()
        symbols = tuple(
            dict.fromkeys(
                value.strip()
                for value in raw_symbols.split(",")
                if value.strip()
            )
        )
        period = os.getenv("AI_TRADING_HOSTED_PERIOD", "1y").strip() or "1y"
        interval = os.getenv("AI_TRADING_HOSTED_INTERVAL", "1d").strip() or "1d"
        poll_seconds = float(os.getenv("AI_TRADING_HOSTED_POLL_SECONDS", "60"))
        shadow_challenger = os.getenv(
            "AI_TRADING_SHADOW_CHALLENGER",
            "0",
        ).strip().lower() in {
            "1",
            "true",
            "yes",
            "on",
        }
        if poll_seconds < 0:
            raise ValueError("AI_TRADING_HOSTED_POLL_SECONDS must be >= 0")
        return cls(
            enabled=enabled,
            external_scheduler=external_scheduler,
            symbol=symbol,
            period=period,
            interval=interval,
            poll_seconds=poll_seconds,
            shadow_challenger=shadow_challenger,
            symbols=symbols,
        )


def _now_utc() -> str:
    return datetime.now(UTC).isoformat()


def run_hosted_paper_loop(
    settings: HostedPaperSettings,
    *,
    persistence: PaperPersistence | None = None,
) -> None:
    print(
        "Hosted paper worker: boot "
        f"symbol={settings.symbol} interval={settings.interval} ",
        f"period={settings.period} poll={settings.poll_seconds:g}s",
        flush=True,
    )
    backend = persistence or build_paper_persistence()
    runtime = PaperAutonomousRuntime(
        symbol=settings.symbol,
        persistence=backend,
        runtime_key=settings.runtime_key,
    )
    backend.save_runtime_status(
        settings.runtime_key,
        HostedRuntimeStatus(
            engine_status="STARTING",
            symbol=settings.symbol,
            interval=settings.interval,
            updated_at_utc=_now_utc(),
            equity=runtime.risk_config.starting_cash,
            poll_seconds=settings.poll_seconds,
        ),
    )
    print("Hosted paper worker: STARTING status persisted", flush=True)
    orchestrator = AutonomousPaperOrchestrator(runtime=runtime)

    def report_iteration(result: OrchestrationResult) -> None:
        step = result.runtime
        backend.save_runtime_status(
            settings.runtime_key,
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
                poll_seconds=settings.poll_seconds,
            ),
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
            run_health_check=False,
        ),
        on_iteration=report_iteration,
    )
    print("Hosted paper worker: entering scheduler loop", flush=True)
    try:
        scheduler.run()
    except Exception as exc:
        try:
            current = backend.load_runtime_status(settings.runtime_key) or HostedRuntimeStatus(
                engine_status="STARTING",
                symbol=settings.symbol,
                interval=settings.interval,
                updated_at_utc=_now_utc(),
                poll_seconds=settings.poll_seconds,
            )
            backend.save_runtime_status(
                settings.runtime_key,
                replace(
                    current,
                    engine_status="ERROR",
                    updated_at_utc=_now_utc(),
                    error=f"{type(exc).__name__}: worker failure",
                ),
            )
        except Exception as status_exc:  # noqa: BLE001 - best-effort failure reporting boundary
            print(
                "Hosted paper worker: ERROR status persistence failed "
                f"({type(status_exc).__name__})",
                flush=True,
            )
        print(
            f"Hosted paper worker: ERROR {type(exc).__name__}",
            flush=True,
        )
        raise


def start_hosted_paper_runtime(
    *,
    settings: HostedPaperSettings | None = None,
    persistence: PaperPersistence | None = None,
    runner: Callable[..., None] = run_hosted_paper_loop,
) -> Thread | None:
    effective_settings = settings or HostedPaperSettings.from_env()
    if not effective_settings.enabled:
        print("Hosted paper worker: disabled", flush=True)
        return None
    if effective_settings.external_scheduler:
        print("Hosted paper worker: external scheduler enabled", flush=True)
        return None

    print("Hosted paper worker: starting daemon thread", flush=True)
    if persistence is None:
        thread = Thread(
            target=runner,
            args=(effective_settings,),
            name="ai-trading-hosted-paper",
            daemon=True,
        )
    else:
        thread = Thread(
            target=runner,
            args=(effective_settings,),
            kwargs={"persistence": persistence},
            name="ai-trading-hosted-paper",
            daemon=True,
        )
    thread.start()
    print("Hosted paper worker: daemon thread started", flush=True)
    return thread

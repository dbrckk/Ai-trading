from __future__ import annotations

import os
from collections.abc import Callable
from dataclasses import dataclass
from threading import Thread

from .data import load_history
from .orchestrator import AutonomousPaperOrchestrator
from .runtime import PaperAutonomousRuntime
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


def run_hosted_paper_loop(settings: HostedPaperSettings) -> None:
    runtime = PaperAutonomousRuntime(symbol=settings.symbol)
    orchestrator = AutonomousPaperOrchestrator(runtime=runtime)
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
    )
    scheduler.run()


def start_hosted_paper_runtime(
    *,
    runner: Callable[[HostedPaperSettings], None] = run_hosted_paper_loop,
) -> Thread | None:
    settings = HostedPaperSettings.from_env()
    if not settings.enabled:
        return None

    thread = Thread(
        target=runner,
        args=(settings,),
        name="ai-trading-hosted-paper",
        daemon=True,
    )
    thread.start()
    return thread

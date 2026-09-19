from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass

from .paper_cycle import PaperCycleResult
from .paper_cycle_service import (
    PaperCycleServiceError,
    ProductionPaperCycleSettings,
    run_production_paper_cycle,
)
from .persistence import PaperPersistence


@dataclass(frozen=True)
class MarketCycleOutcome:
    symbol: str
    ok: bool
    processed: int
    processed_bars: int
    last_processed: str | None
    reason: str


@dataclass(frozen=True)
class MultiMarketCycleResult:
    outcomes: tuple[MarketCycleOutcome, ...]

    @property
    def processed(self) -> int:
        return sum(outcome.processed for outcome in self.outcomes if outcome.ok)

    @property
    def successful_markets(self) -> int:
        return sum(1 for outcome in self.outcomes if outcome.ok)

    @property
    def failed_markets(self) -> int:
        return sum(1 for outcome in self.outcomes if not outcome.ok)

    def as_paper_cycle_result(self) -> PaperCycleResult:
        successful = [outcome for outcome in self.outcomes if outcome.ok]
        last_processed = None
        if successful:
            timestamps = [
                outcome.last_processed
                for outcome in successful
                if outcome.last_processed is not None
            ]
            last_processed = max(timestamps) if timestamps else None
        return PaperCycleResult(
            processed=self.processed,
            remaining_backlog=any(
                outcome.reason == "catch-up pending"
                for outcome in successful
            ),
            last_processed=last_processed,
            processed_bars=sum(outcome.processed_bars for outcome in successful),
            reason=(
                f"markets ok={self.successful_markets} "
                f"failed={self.failed_markets} processed={self.processed}"
            ),
        )


def run_production_multi_market_cycle(
    settings: tuple[ProductionPaperCycleSettings, ...],
    *,
    persistence: PaperPersistence,
    max_workers: int | None = None,
) -> MultiMarketCycleResult:
    if not settings:
        raise ValueError("at least one market setting is required")

    workers = max_workers or min(4, len(settings))
    outcomes: list[MarketCycleOutcome] = []

    def run_one(config: ProductionPaperCycleSettings) -> MarketCycleOutcome:
        try:
            result = run_production_paper_cycle(
                config,
                persistence=persistence,
            )
            return MarketCycleOutcome(
                symbol=config.symbol,
                ok=True,
                processed=result.processed,
                processed_bars=result.processed_bars,
                last_processed=result.last_processed,
                reason=result.reason,
            )
        except PaperCycleServiceError as exc:
            return MarketCycleOutcome(
                symbol=config.symbol,
                ok=False,
                processed=0,
                processed_bars=0,
                last_processed=None,
                reason=exc.code,
            )

    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {executor.submit(run_one, config): config.symbol for config in settings}
        for future in as_completed(futures):
            outcomes.append(future.result())

    outcomes.sort(key=lambda outcome: outcome.symbol)
    aggregate = MultiMarketCycleResult(tuple(outcomes))
    if aggregate.successful_markets == 0:
        raise PaperCycleServiceError(
            code="execution_failed",
            error_type="MultiMarketCycleError",
        )
    return aggregate

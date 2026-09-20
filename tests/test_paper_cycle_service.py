from __future__ import annotations

import pytest

from ai_trading.paper_cycle import PaperCycleResult
from ai_trading.paper_cycle_service import (
    PaperCycleServiceError,
    ProductionPaperCycleSettings,
    run_production_paper_cycle,
)
from ai_trading.persistence import PersistedRuntime
from ai_trading.runtime_state import RuntimeState
from ai_trading.runtime_status import HostedRuntimeStatus


class FakePersistence:
    def __init__(self, *, initial_status: HostedRuntimeStatus | None = None) -> None:
        self.statuses: list[HostedRuntimeStatus] = []
        self.initial_status = initial_status
        self.state = RuntimeState(
            cash=99_500.0,
            units=2.0,
            last_price=101.0,
            peak_equity=100_000.0,
            day_start_equity=100_000.0,
            last_processed="2026-09-16 08:00:00+00:00",
            processed_bars=4,
            last_learning_cycle_bar=0,
        )

    def save_runtime_status(self, runtime_key: str, status: HostedRuntimeStatus) -> None:
        assert runtime_key == "paper:GC=F:5m:online-river:v1"
        self.statuses.append(status)

    def load_runtime_status(self, runtime_key: str) -> HostedRuntimeStatus | None:
        assert runtime_key == "paper:GC=F:5m:online-river:v1"
        return self.statuses[-1] if self.statuses else self.initial_status

    def load_runtime(self, runtime_key: str, starting_cash: float) -> PersistedRuntime:
        assert runtime_key == "paper:GC=F:5m:online-river:v1"
        assert starting_cash == 100_000.0
        return PersistedRuntime(state=self.state, model=None, revision=4, is_new=False)


class FakeRunner:
    def __init__(self, persistence: FakePersistence) -> None:
        self.persistence = persistence
        self.shadow_challenger_enabled = False
        self.mtf_period = None

    def run_once(
        self,
        *,
        symbol: str,
        period: str,
        interval: str,
        max_catchup_bars: int,
        shadow_challenger_enabled: bool = False,
        mtf_period: str | None = None,
    ) -> PaperCycleResult:
        self.shadow_challenger_enabled = shadow_challenger_enabled
        self.mtf_period = mtf_period
        assert (symbol, period, interval, max_catchup_bars) == (
            "GC=F",
            "5d",
            "5m",
            72,
        )
        return PaperCycleResult(
            processed=2,
            remaining_backlog=False,
            last_processed="2026-09-16 08:00:00+00:00",
            processed_bars=4,
            reason="processed 2 bar(s)",
        )


def test_service_persists_starting_and_running_status() -> None:
    backend = FakePersistence()
    result = run_production_paper_cycle(
        ProductionPaperCycleSettings(),
        persistence=backend,
        runner_factory=lambda persistence: FakeRunner(persistence),
    )

    assert result.processed == 2
    assert [status.engine_status for status in backend.statuses] == ["STARTING", "RUNNING"]
    final = backend.statuses[-1]
    assert final.symbol == "GC=F"
    assert final.interval == "5m"
    assert final.poll_seconds == 300.0
    assert final.processed is True
    assert final.processed_bars == 4
    assert final.units == 2.0
    assert final.equity == 99_702.0
    assert final.reason == "processed 2 bar(s)"


def test_persistence_factory_failure_is_sanitized() -> None:
    def broken_factory():
        raise RuntimeError("postgresql://user:secret@example.invalid/private")

    with pytest.raises(PaperCycleServiceError) as caught:
        run_production_paper_cycle(
            ProductionPaperCycleSettings(),
            persistence_factory=broken_factory,
        )

    error = caught.value
    assert error.code == "storage_unavailable"
    assert error.error_type == "RuntimeError"
    assert error.__cause__ is None
    assert "postgresql://" not in str(error)
    assert "secret" not in repr(error)
    assert "example.invalid" not in repr(error)


def test_starting_status_failure_never_runs_worker() -> None:
    backend = FakePersistence()
    calls = 0

    def broken_save(runtime_key, status):
        del runtime_key, status
        raise RuntimeError("storage down")

    backend.save_runtime_status = broken_save

    def runner_factory(persistence):
        nonlocal calls
        del persistence
        calls += 1
        return FakeRunner(backend)

    with pytest.raises(PaperCycleServiceError) as caught:
        run_production_paper_cycle(
            ProductionPaperCycleSettings(),
            persistence=backend,
            runner_factory=runner_factory,
        )

    assert calls == 0
    assert caught.value.code == "storage_unavailable"
    assert caught.value.__cause__ is None


def test_worker_failure_writes_sanitized_error_status() -> None:
    backend = FakePersistence()

    class BrokenRunner:
        def run_once(self, **kwargs):
            del kwargs
            raise RuntimeError("postgresql://user:secret@example.invalid/private")

    with pytest.raises(PaperCycleServiceError) as caught:
        run_production_paper_cycle(
            ProductionPaperCycleSettings(),
            persistence=backend,
            runner_factory=lambda persistence: BrokenRunner(),
        )

    assert [status.engine_status for status in backend.statuses] == ["STARTING", "ERROR"]
    assert backend.statuses[-1].error == "RuntimeError: worker failure"
    assert caught.value.code == "execution_failed"
    assert caught.value.error_type == "RuntimeError"
    assert caught.value.__cause__ is None
    assert "secret" not in repr(caught.value)


def test_error_status_failure_does_not_mask_worker_failure() -> None:
    backend = FakePersistence()
    original_save = backend.save_runtime_status
    writes = 0

    def flaky_save(runtime_key, status):
        nonlocal writes
        writes += 1
        if writes >= 2:
            raise RuntimeError("status write failed with secret")
        original_save(runtime_key, status)

    backend.save_runtime_status = flaky_save

    class BrokenRunner:
        def run_once(self, **kwargs):
            del kwargs
            raise ValueError("provider secret")

    with pytest.raises(PaperCycleServiceError) as caught:
        run_production_paper_cycle(
            ProductionPaperCycleSettings(),
            persistence=backend,
            runner_factory=lambda persistence: BrokenRunner(),
        )

    assert caught.value.code == "execution_failed"
    assert caught.value.error_type == "ValueError"
    assert caught.value.__cause__ is None


def test_success_resets_consecutive_cycle_errors() -> None:
    backend = FakePersistence(
        initial_status=HostedRuntimeStatus(
            engine_status="ERROR",
            symbol="GC=F",
            interval="5m",
            updated_at_utc="2026-09-18T15:00:00+00:00",
            consecutive_cycle_errors=2,
            error="RuntimeError: worker failure",
            poll_seconds=300.0,
        )
    )

    run_production_paper_cycle(
        ProductionPaperCycleSettings(),
        persistence=backend,
        runner_factory=lambda persistence: FakeRunner(persistence),
    )

    assert backend.statuses[0].engine_status == "STARTING"
    assert backend.statuses[0].consecutive_cycle_errors == 2
    assert backend.statuses[-1].engine_status == "RUNNING"
    assert backend.statuses[-1].consecutive_cycle_errors == 0


def test_failure_increments_consecutive_cycle_errors() -> None:
    backend = FakePersistence(
        initial_status=HostedRuntimeStatus(
            engine_status="ERROR",
            symbol="GC=F",
            interval="5m",
            updated_at_utc="2026-09-18T15:00:00+00:00",
            consecutive_cycle_errors=2,
            error="RuntimeError: worker failure",
            poll_seconds=300.0,
        )
    )

    class BrokenRunner:
        def run_once(self, **kwargs):
            del kwargs
            raise RuntimeError("provider failure")

    with pytest.raises(PaperCycleServiceError):
        run_production_paper_cycle(
            ProductionPaperCycleSettings(),
            persistence=backend,
            runner_factory=lambda persistence: BrokenRunner(),
        )

    assert backend.statuses[0].engine_status == "STARTING"
    assert backend.statuses[0].consecutive_cycle_errors == 2
    assert backend.statuses[-1].engine_status == "ERROR"
    assert backend.statuses[-1].consecutive_cycle_errors == 3



def test_service_propagates_shadow_challenger_when_enabled() -> None:
    backend = FakePersistence()
    runner = FakeRunner(backend)

    result = run_production_paper_cycle(
        ProductionPaperCycleSettings(shadow_challenger_enabled=True),
        persistence=backend,
        runner_factory=lambda persistence: runner,
    )

    assert result.processed == 2
    assert runner.shadow_challenger_enabled is True



def test_service_propagates_separate_mtf_period() -> None:
    backend = FakePersistence()
    runner = FakeRunner(backend)

    run_production_paper_cycle(
        ProductionPaperCycleSettings(
            shadow_challenger_enabled=True,
            mtf_period="1mo",
        ),
        persistence=backend,
        runner_factory=lambda persistence: runner,
    )

    assert runner.shadow_challenger_enabled is True
    assert runner.mtf_period == "1mo"

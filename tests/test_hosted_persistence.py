from __future__ import annotations

from types import SimpleNamespace

import pytest

from ai_trading import hosted_runtime
from ai_trading.hosted_runtime import HostedPaperSettings
from ai_trading.runtime_status import HostedRuntimeStatus

RUNTIME_KEY = "paper:GC=F:5m:online-river:v1"


class RecordingPersistence:
    def __init__(self) -> None:
        self.statuses: list[tuple[str, HostedRuntimeStatus]] = []

    def save_runtime_status(self, runtime_key: str, status: HostedRuntimeStatus) -> None:
        self.statuses.append((runtime_key, status))

    def load_runtime_status(self, runtime_key: str) -> HostedRuntimeStatus | None:
        for key, status in reversed(self.statuses):
            if key == runtime_key:
                return status
        return None


def _settings() -> HostedPaperSettings:
    return HostedPaperSettings(
        enabled=True,
        symbol="GC=F",
        period="5d",
        interval="5m",
        poll_seconds=120.0,
    )


def _raising_scheduler(monkeypatch) -> None:
    class RaisingScheduler:
        def __init__(self, **kwargs) -> None:
            return None

        def run(self) -> None:
            raise RuntimeError("forced worker failure")

    monkeypatch.setattr(hosted_runtime, "PaperScheduler", RaisingScheduler)


def _fake_runtime(monkeypatch) -> None:
    monkeypatch.setattr(
        hosted_runtime,
        "PaperAutonomousRuntime",
        lambda **kwargs: SimpleNamespace(risk_config=SimpleNamespace(starting_cash=100_000.0)),
    )
    monkeypatch.setattr(hosted_runtime, "AutonomousPaperOrchestrator", lambda runtime: object())


def test_hosted_settings_exposes_stable_runtime_key() -> None:
    assert _settings().runtime_key == RUNTIME_KEY


def test_hosted_loop_shares_backend_and_runtime_key(monkeypatch) -> None:
    persistence = RecordingPersistence()
    captured: dict[str, object] = {}

    def fake_runtime(**kwargs):
        captured["runtime_kwargs"] = kwargs
        return SimpleNamespace(risk_config=SimpleNamespace(starting_cash=100_000.0))

    class FakeScheduler:
        def __init__(self, **kwargs) -> None:
            self.on_iteration = kwargs["on_iteration"]
            captured["config"] = kwargs["config"]

        def run(self) -> list[object]:
            self.on_iteration(
                SimpleNamespace(
                    runtime=SimpleNamespace(
                        timestamp="2026-09-15T20:00:00+00:00",
                        processed=True,
                        side=1,
                        confidence=0.75,
                        approved=True,
                        reason="approved",
                        equity=100_123.0,
                        units=1.0,
                        processed_bars=4,
                    )
                )
            )
            return []

    monkeypatch.setattr(hosted_runtime, "PaperAutonomousRuntime", fake_runtime)
    monkeypatch.setattr(hosted_runtime, "AutonomousPaperOrchestrator", lambda runtime: object())
    monkeypatch.setattr(hosted_runtime, "PaperScheduler", FakeScheduler)

    hosted_runtime.run_hosted_paper_loop(_settings(), persistence=persistence)

    runtime_kwargs = captured["runtime_kwargs"]
    assert runtime_kwargs["symbol"] == "GC=F"
    assert runtime_kwargs["persistence"] is persistence
    assert runtime_kwargs["runtime_key"] == RUNTIME_KEY
    assert [status.engine_status for _, status in persistence.statuses] == ["STARTING", "RUNNING"]
    assert {key for key, _ in persistence.statuses} == {RUNTIME_KEY}
    assert captured["config"].run_health_check is False


def test_hosted_loop_persists_error_status(monkeypatch) -> None:
    persistence = RecordingPersistence()
    _fake_runtime(monkeypatch)
    _raising_scheduler(monkeypatch)

    with pytest.raises(RuntimeError, match="forced worker failure"):
        hosted_runtime.run_hosted_paper_loop(_settings(), persistence=persistence)

    assert persistence.statuses[-1][0] == RUNTIME_KEY
    assert persistence.statuses[-1][1].engine_status == "ERROR"


def test_worker_error_is_not_masked_when_status_storage_is_unavailable(monkeypatch) -> None:
    class FailingStatusPersistence(RecordingPersistence):
        def load_runtime_status(self, runtime_key: str) -> HostedRuntimeStatus | None:
            del runtime_key
            raise RuntimeError("storage failure")

    persistence = FailingStatusPersistence()
    _fake_runtime(monkeypatch)
    _raising_scheduler(monkeypatch)

    with pytest.raises(RuntimeError, match="forced worker failure"):
        hosted_runtime.run_hosted_paper_loop(_settings(), persistence=persistence)


def test_start_worker_can_reuse_injected_backend() -> None:
    persistence = RecordingPersistence()
    seen: list[tuple[HostedPaperSettings, object]] = []

    def runner(settings: HostedPaperSettings, *, persistence) -> None:
        seen.append((settings, persistence))

    thread = hosted_runtime.start_hosted_paper_runtime(
        settings=_settings(),
        persistence=persistence,
        runner=runner,
    )

    assert thread is not None
    thread.join(timeout=1.0)
    assert seen == [(_settings(), persistence)]

from __future__ import annotations

from threading import Event
from types import SimpleNamespace

from ai_trading import hosted_runtime
from ai_trading.hosted_runtime import HostedPaperSettings, start_hosted_paper_runtime


def test_hosted_paper_settings_disabled_by_default(monkeypatch) -> None:
    monkeypatch.delenv("AI_TRADING_HOSTED_PAPER", raising=False)
    monkeypatch.delenv("AI_TRADING_EXTERNAL_SCHEDULER", raising=False)
    monkeypatch.delenv("AI_TRADING_HOSTED_SYMBOL", raising=False)
    monkeypatch.delenv("AI_TRADING_HOSTED_PERIOD", raising=False)
    monkeypatch.delenv("AI_TRADING_HOSTED_INTERVAL", raising=False)
    monkeypatch.delenv("AI_TRADING_HOSTED_POLL_SECONDS", raising=False)

    settings = HostedPaperSettings.from_env()

    assert settings.enabled is False
    assert settings.external_scheduler is False
    assert settings.symbol == "GC=F"
    assert settings.period == "1y"
    assert settings.interval == "1d"
    assert settings.poll_seconds == 60.0


def test_enabled_hosted_runtime_starts_daemon_worker(monkeypatch) -> None:
    monkeypatch.setenv("AI_TRADING_HOSTED_PAPER", "1")
    monkeypatch.delenv("AI_TRADING_EXTERNAL_SCHEDULER", raising=False)
    monkeypatch.setenv("AI_TRADING_HOSTED_SYMBOL", "SI=F")
    monkeypatch.setenv("AI_TRADING_HOSTED_POLL_SECONDS", "15")
    called = Event()
    seen: list[HostedPaperSettings] = []

    def runner(settings: HostedPaperSettings) -> None:
        seen.append(settings)
        called.set()

    thread = start_hosted_paper_runtime(runner=runner)

    assert thread is not None
    thread.join(timeout=1.0)
    assert called.is_set()
    assert thread.daemon is True
    assert seen[0].symbol == "SI=F"
    assert seen[0].poll_seconds == 15.0


def test_external_scheduler_suppresses_daemon(monkeypatch) -> None:
    monkeypatch.setenv("AI_TRADING_HOSTED_PAPER", "1")
    monkeypatch.setenv("AI_TRADING_EXTERNAL_SCHEDULER", "1")
    settings = HostedPaperSettings.from_env()

    thread = start_hosted_paper_runtime(settings=settings, runner=lambda _: None)

    assert settings.external_scheduler is True
    assert thread is None


def test_hosted_loop_disables_expensive_health_check(monkeypatch) -> None:
    captured: dict[str, object] = {}

    class FakePersistence:
        def __init__(self) -> None:
            self.status = None

        def save_runtime_status(self, runtime_key, status) -> None:
            del runtime_key
            self.status = status

        def load_runtime_status(self, runtime_key):
            del runtime_key
            return self.status

    class FakeScheduler:
        def __init__(self, **kwargs) -> None:
            captured["config"] = kwargs["config"]

        def run(self) -> list[object]:
            return []

    fake_runtime = SimpleNamespace(
        risk_config=SimpleNamespace(starting_cash=100_000.0),
    )
    monkeypatch.setattr(
        hosted_runtime,
        "PaperAutonomousRuntime",
        lambda **kwargs: fake_runtime,
    )
    monkeypatch.setattr(
        hosted_runtime,
        "AutonomousPaperOrchestrator",
        lambda runtime: object(),
    )
    monkeypatch.setattr(hosted_runtime, "PaperScheduler", FakeScheduler)

    hosted_runtime.run_hosted_paper_loop(
        HostedPaperSettings(
            enabled=True,
            symbol="GC=F",
            period="5d",
            interval="5m",
            poll_seconds=120.0,
        ),
        persistence=FakePersistence(),
    )

    config = captured["config"]
    assert config.run_health_check is False

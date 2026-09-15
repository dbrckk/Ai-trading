from __future__ import annotations

from threading import Event

from ai_trading.hosted_runtime import HostedPaperSettings, start_hosted_paper_runtime


def test_hosted_paper_settings_disabled_by_default(monkeypatch) -> None:
    monkeypatch.delenv("AI_TRADING_HOSTED_PAPER", raising=False)
    monkeypatch.delenv("AI_TRADING_HOSTED_SYMBOL", raising=False)

    settings = HostedPaperSettings.from_env()

    assert settings.enabled is False
    assert settings.symbol == "GC=F"
    assert settings.period == "1y"
    assert settings.interval == "1d"
    assert settings.poll_seconds == 60.0


def test_enabled_hosted_runtime_starts_daemon_worker(monkeypatch) -> None:
    monkeypatch.setenv("AI_TRADING_HOSTED_PAPER", "1")
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

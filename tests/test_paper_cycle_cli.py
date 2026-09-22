from typer.testing import CliRunner

from ai_trading import command_app
from ai_trading.paper_cycle import PaperCycleResult
from ai_trading.paper_cycle_service import (
    PaperCycleServiceError,
    ProductionPaperCycleSettings,
)

runner = CliRunner()


def test_cli_calls_shared_production_service(monkeypatch) -> None:
    seen: list[ProductionPaperCycleSettings] = []

    def fake_service(settings: ProductionPaperCycleSettings) -> PaperCycleResult:
        seen.append(settings)
        return PaperCycleResult(
            processed=1,
            remaining_backlog=False,
            last_processed="2026-09-16 08:00:00+00:00",
            processed_bars=4,
            reason="processed 1 bar(s)",
        )

    monkeypatch.setattr(command_app, "run_production_paper_cycle", fake_service)
    result = runner.invoke(
        command_app.app,
        [
            "paper-cycle",
            "--symbol",
            "GC=F",
            "--period",
            "5d",
            "--interval",
            "5m",
            "--max-catchup-bars",
            "12",
        ],
    )

    assert result.exit_code == 0
    assert seen == [
        ProductionPaperCycleSettings(
            symbol="GC=F",
            period="5d",
            interval="5m",
            max_catchup_bars=12,
            poll_seconds=300.0,
        )
    ]
    assert "processed 1 bar(s)" in result.output
    assert "processed_bars=4" in result.output


def test_cli_sanitizes_shared_service_failure(monkeypatch) -> None:
    def fail(settings: ProductionPaperCycleSettings) -> PaperCycleResult:
        del settings
        raise PaperCycleServiceError(
            code="execution_failed",
            error_type="RuntimeError",
        )

    monkeypatch.setattr(command_app, "run_production_paper_cycle", fail)
    result = runner.invoke(command_app.app, ["paper-cycle"])

    assert result.exit_code != 0
    assert "execution_failed" in result.output
    assert "RuntimeError" in result.output
    assert "postgresql://" not in result.output
    assert "secret" not in result.output
    assert "postgresql://" not in str(result.exception)


def test_multi_market_cli_uses_configured_market_bundle(monkeypatch) -> None:
    seen: list[dict[str, object]] = []

    monkeypatch.setattr(command_app, "configured_markets_from_env", lambda: DEFAULT_MARKETS)

    def fake_multi_market(markets, **kwargs) -> PaperCycleResult:
        seen.append({"markets": markets, **kwargs})
        return PaperCycleResult(
            processed=3,
            remaining_backlog=False,
            last_processed="2026-09-22 12:00:00+00:00",
            processed_bars=9,
            reason="processed 3 bar(s) across 3 market(s)",
        )

    monkeypatch.setattr(command_app, "run_multi_market_paper_cycle", fake_multi_market)
    result = runner.invoke(
        command_app.app,
        [
            "paper-cycle-all",
            "--period",
            "5d",
            "--interval",
            "5m",
            "--max-catchup-bars",
            "24",
        ],
    )

    assert result.exit_code == 0
    assert seen == [
        {
            "markets": DEFAULT_MARKETS,
            "period": "5d",
            "interval": "5m",
            "max_catchup_bars": 24,
            "poll_seconds": 300.0,
            "shadow_challenger_enabled": False,
        }
    ]
    assert "across 3 market(s)" in result.output
    assert "processed_bars=9" in result.output


def test_multi_market_cli_sanitizes_invalid_configuration(monkeypatch) -> None:
    def invalid_markets():
        raise ValueError("secret provider detail")

    monkeypatch.setattr(command_app, "configured_markets_from_env", invalid_markets)
    result = runner.invoke(command_app.app, ["paper-cycle-all"])

    assert result.exit_code != 0
    assert "configuration_invalid" in result.output
    assert "secret provider detail" not in result.output

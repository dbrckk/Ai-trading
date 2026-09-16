from types import SimpleNamespace

from typer.testing import CliRunner

from ai_trading import command_app as cli
from ai_trading.paper_cycle import PaperCycleResult
from ai_trading.runtime_state import RuntimeState

runner = CliRunner()


class FakePersistence:
    def __init__(self, *, fail_error_status: bool = False) -> None:
        self.statuses = []
        self.fail_error_status = fail_error_status
        self.state = RuntimeState(
            cash=99_500.0,
            units=2.0,
            last_price=101.0,
            peak_equity=100_000.0,
            day_start_equity=100_000.0,
            last_processed="2026-09-16 06:30:00+00:00",
            processed_bars=4,
            last_learning_cycle_bar=0,
        )

    def save_runtime_status(self, runtime_key, status) -> None:
        del runtime_key
        if self.fail_error_status and status.engine_status == "ERROR":
            raise OSError("status backend details must stay private")
        self.statuses.append(status)

    def load_runtime(self, runtime_key, starting_cash):
        del runtime_key, starting_cash
        return SimpleNamespace(state=self.state)


def test_paper_cycle_cli_runs_once_and_persists_status(monkeypatch) -> None:
    backend = FakePersistence()
    seen: dict[str, object] = {}

    class FakeRunner:
        def __init__(self, *, persistence) -> None:
            seen["persistence"] = persistence

        def run_once(self, **kwargs) -> PaperCycleResult:
            seen.update(kwargs)
            return PaperCycleResult(
                processed=2,
                remaining_backlog=False,
                last_processed="2026-09-16 06:30:00+00:00",
                processed_bars=4,
                reason="processed 2 bar(s)",
            )

    monkeypatch.setattr(cli, "build_paper_persistence", lambda: backend)
    monkeypatch.setattr(cli, "PaperCycleRunner", FakeRunner)

    result = runner.invoke(
        cli.app,
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
    assert seen == {
        "persistence": backend,
        "symbol": "GC=F",
        "period": "5d",
        "interval": "5m",
        "max_catchup_bars": 12,
    }
    assert [status.engine_status for status in backend.statuses] == ["STARTING", "RUNNING"]
    final = backend.statuses[-1]
    assert final.poll_seconds == 300.0
    assert final.processed is True
    assert final.processed_bars == 4
    assert final.units == 2.0
    assert final.equity == 99_702.0
    assert final.reason == "processed 2 bar(s)"


def test_paper_cycle_cli_persistence_initialization_failure_is_sanitized(monkeypatch) -> None:
    def fail_to_build():
        raise RuntimeError("postgresql://user:supersecret@db.internal.example/private")

    monkeypatch.setattr(cli, "build_paper_persistence", fail_to_build)

    result = runner.invoke(cli.app, ["paper-cycle"])

    assert result.exit_code != 0
    assert "supersecret" not in result.output
    assert "db.internal.example" not in result.output
    assert "postgresql://" not in result.output
    assert "supersecret" not in str(result.exception)
    assert "db.internal.example" not in str(result.exception)
    assert "postgresql://" not in str(result.exception)


def test_paper_cycle_cli_failure_is_sanitized_and_nonzero(monkeypatch) -> None:
    backend = FakePersistence()

    class FailingRunner:
        def __init__(self, *, persistence) -> None:
            del persistence

        def run_once(self, **kwargs):
            del kwargs
            raise RuntimeError("database-url-password=supersecret")

    monkeypatch.setattr(cli, "build_paper_persistence", lambda: backend)
    monkeypatch.setattr(cli, "PaperCycleRunner", FailingRunner)

    result = runner.invoke(cli.app, ["paper-cycle"])

    assert result.exit_code != 0
    assert "supersecret" not in result.output
    assert backend.statuses[-1].engine_status == "ERROR"
    assert backend.statuses[-1].error == "RuntimeError: worker failure"


def test_error_status_failure_does_not_leak_or_replace_executor_failure(monkeypatch) -> None:
    backend = FakePersistence(fail_error_status=True)

    class FailingRunner:
        def __init__(self, *, persistence) -> None:
            del persistence

        def run_once(self, **kwargs):
            del kwargs
            raise RuntimeError("executor-secret-message")

    monkeypatch.setattr(cli, "build_paper_persistence", lambda: backend)
    monkeypatch.setattr(cli, "PaperCycleRunner", FailingRunner)

    result = runner.invoke(cli.app, ["paper-cycle"])

    assert result.exit_code != 0
    assert "executor-secret-message" not in result.output
    assert "status backend details" not in result.output
    assert [status.engine_status for status in backend.statuses] == ["STARTING"]

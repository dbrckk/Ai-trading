from pathlib import Path

from ai_trading.cli import app
from typer.testing import CliRunner


runner = CliRunner()


def test_self_test_command_runs_offline(tmp_path: Path) -> None:
    workspace = tmp_path / "self-test"

    result = runner.invoke(
        app,
        ["self-test", "--workspace", str(workspace)],
    )

    assert result.exit_code == 0, result.output
    assert "SELF-TEST PASS" in result.output
    assert (workspace / "snapshots").exists()
    assert (workspace / "heartbeat.json").exists()

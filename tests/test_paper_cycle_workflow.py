from __future__ import annotations

import os
import subprocess
from pathlib import Path
from textwrap import dedent

WORKFLOW_PATH = Path(".github/workflows/paper-cycle.yml")
STEP_HEADER = (
    "      - name: Run all three paper markets\n"
    "        shell: bash\n"
    "        run: |\n"
)


def _fallback_script() -> str:
    workflow = WORKFLOW_PATH.read_text(encoding="utf-8")
    # This is the actual shell body GitHub Actions runs, not a copied command.
    body = workflow.split(STEP_HEADER, 1)[1]
    return dedent(body.split("\n      - ", 1)[0])


def test_paper_cycle_workflow_structure() -> None:
    assert WORKFLOW_PATH.exists()
    text = WORKFLOW_PATH.read_text(encoding="utf-8")

    required = (
        'cron: "7-57/5 * * * *"',
        "timeout-minutes: 15",
        "workflow_dispatch:",
        "group: paper-cycle-production",
        "cancel-in-progress: false",
        "AI_TRADING_DATABASE_URL: ${{ secrets.AI_TRADING_DATABASE_URL }}",
        'if [ -z "${AI_TRADING_DATABASE_URL:-}" ]; then',
        "AI_TRADING_DATABASE_URL repository secret is required",
        "for symbol in GC=F ^GDAXI BTC-USD; do",
        '--symbol "${symbol}" --period 5d --interval 5m --max-catchup-bars 72',
        "|| failures=$((failures + 1))",
        'if [ "${failures}" -gt 0 ]; then',
        'echo "::error::${failures} market paper cycle(s) failed"',
    )
    for expected in required:
        assert expected in text

    for forbidden in ("postgresql://", "postgres://", "password="):
        assert forbidden not in text


def test_fallback_runs_every_market_even_after_failure(tmp_path: Path) -> None:
    for failed_market, expected_code in (("GC=F", 1), ("", 0)):
        (tmp_path / "visited-markets.txt").write_text("", encoding="utf-8")
        market_log = tmp_path / "visited-markets.txt"
        fake_cli = tmp_path / "ai-trading"
        fake_cli.write_text(
            "#!/bin/sh\n"
            'printf "%s\\n" "$3" >> "$FAKE_MARKET_LOG"\n'
            '[ "$3" != "$FAKE_FAIL_MARKET" ]\n',
            encoding="utf-8",
        )
        fake_cli.chmod(0o755)
        result = subprocess.run(
            ["bash", "-e", "-c", _fallback_script()],
            env={
                **os.environ,
                "PATH": f"{tmp_path}:{os.environ.get('PATH', '')}",
                "FAKE_MARKET_LOG": str(market_log),
                "FAKE_FAIL_MARKET": failed_market,
            },
            capture_output=True,
            text=True,
            check=False,
        )

        assert market_log.read_text(encoding="utf-8").splitlines() == [
            "GC=F",
            "^GDAXI",
            "BTC-USD",
        ]
        assert result.returncode == expected_code
        if failed_market:
            assert "::error::1 market paper cycle(s) failed" in result.stdout

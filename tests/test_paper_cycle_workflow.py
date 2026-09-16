from pathlib import Path


def test_paper_cycle_workflow_structure() -> None:
    path = Path(".github/workflows/paper-cycle.yml")
    assert path.exists()
    text = path.read_text(encoding="utf-8")

    required = (
        'cron: "*/5 * * * *"',
        "workflow_dispatch:",
        "group: paper-cycle-production",
        "cancel-in-progress: false",
        "AI_TRADING_DATABASE_URL: ${{ secrets.AI_TRADING_DATABASE_URL }}",
        "ai-trading paper-cycle --symbol GC=F --period 5d --interval 5m --max-catchup-bars 12",
    )
    for expected in required:
        assert expected in text

    for forbidden in ("postgresql://", "postgres://", "password="):
        assert forbidden not in text

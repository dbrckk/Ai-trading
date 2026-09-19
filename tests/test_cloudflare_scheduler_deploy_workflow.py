from pathlib import Path


def test_cloudflare_scheduler_deploy_workflow_is_fail_closed() -> None:
    path = Path(".github/workflows/cloudflare-paper-scheduler-deploy.yml")
    assert path.exists()
    text = path.read_text(encoding="utf-8")

    required = (
        "workflow_dispatch:",
        'branches: ["main"]',
        'vars.CLOUDFLARE_SCHEDULER_ENABLED == \'true\'',
        "group: cloudflare-paper-scheduler-deploy",
        "cancel-in-progress: true",
        "actions/checkout@v6",
        "cloudflare/wrangler-action@v4",
        "CLOUDFLARE_API_TOKEN: ${{ secrets.CLOUDFLARE_API_TOKEN }}",
        "CLOUDFLARE_ACCOUNT_ID: ${{ secrets.CLOUDFLARE_ACCOUNT_ID }}",
        "SCHEDULER_TOKEN: ${{ secrets.AI_TRADING_SCHEDULER_TOKEN }}",
        "workingDirectory: infra/cloudflare-paper-scheduler",
        "command: deploy",
        "secrets: |",
    )
    for expected in required:
        assert expected in text

    assert "schedule:" not in text
    assert "cron:" not in text
    for forbidden in (
        "postgresql://",
        "postgres://",
        "password=",
        "scheduler-secret",
        "expected-token",
    ):
        assert forbidden not in text

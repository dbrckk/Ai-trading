from pathlib import Path


def test_render_blueprint_uses_readiness_and_external_multi_market_scheduler() -> None:
    text = Path("render.yaml").read_text(encoding="utf-8")

    required = (
        "autoDeployTrigger: checksPass",
        "healthCheckPath: /readyz",
        "buildFilter:",
        '".ai/**"',
        '".serena/**"',
        "AI_TRADING_HOSTED_PAPER",
        "AI_TRADING_EXTERNAL_SCHEDULER",
        "AI_TRADING_MARKETS",
        '"GC=F,^GDAXI,BTC-USD"',
        "AI_TRADING_HOSTED_PERIOD",
        '"5d"',
        "AI_TRADING_HOSTED_INTERVAL",
        '"5m"',
        "AI_TRADING_DATABASE_URL",
        "AI_TRADING_SCHEDULER_TOKEN",
        "sync: false",
    )
    for expected in required:
        assert expected in text

    for forbidden in ("postgresql://", "postgres://", "password="):
        assert forbidden not in text

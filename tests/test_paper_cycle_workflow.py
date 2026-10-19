from __future__ import annotations

import json
from io import BytesIO
from pathlib import Path
from urllib.error import HTTPError, URLError

import pytest

from ai_trading.scheduler_fallback import FallbackFailure, _recent_cloudflare, run_fallback

WORKFLOW_PATH = Path(".github/workflows/paper-cycle.yml")
WORKER_CONFIG_PATH = Path("infra/cloudflare-paper-scheduler/wrangler.toml")


class FakeResponse:
    status = 200

    def __init__(self, payload: dict[str, object], *, status: int = 200) -> None:
        self.status = status
        self.content = BytesIO(json.dumps(payload).encode())

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self, size: int) -> bytes:
        return self.content.read(size)


def test_paper_cycle_workflow_uses_authenticated_render_not_expired_db() -> None:
    text = WORKFLOW_PATH.read_text(encoding="utf-8")
    worker = WORKER_CONFIG_PATH.read_text(encoding="utf-8")
    required = (
        'cron: "3 * * * *"',
        "workflow_dispatch:",
        "timeout-minutes: 15",
        "group: paper-cycle-production",
        "cancel-in-progress: false",
        "AI_TRADING_SCHEDULER_TOKEN: ${{ secrets.AI_TRADING_SCHEDULER_TOKEN }}",
        "AI_TRADING_SCHEDULER_TOKEN repository secret is required",
        "python -m ai_trading.scheduler_fallback",
        "https://ai-trading-dashboard-qyr2.onrender.com",
        'PYTHONPATH: src',
    )
    for expected in required:
        assert expected in text
    assert 'crons = ["*/15 * * * *"]' in worker
    assert "secrets.AI_TRADING_DATABASE_URL" not in text
    assert "pip install" not in text
    for forbidden in ("postgresql://", "postgres://", "password="):
        assert forbidden not in text


@pytest.mark.parametrize("age_seconds", [8 * 60, 13 * 60, 30 * 60, 32 * 60])
def test_fallback_skips_healthy_recent_cloudflare_without_paper_post(
    age_seconds: int,
) -> None:
    seen = []

    def fake_open(request, timeout):
        seen.append((request.get_method(), request.full_url, timeout))
        return FakeResponse(
            {
                "last_source": "cloudflare",
                "last_status_code": 200,
                "last_ok": True,
                "last_delivery_age_seconds": age_seconds,
            }
        )

    outcome = run_fallback("https://example.invalid", "server-secret", opener=fake_open)
    assert outcome == "skipped_recent_cloudflare"
    assert seen == [("GET", "https://example.invalid/api/scheduler", 90.0)]


@pytest.mark.parametrize(
    "status_payload",
    [
        {},
        {"last_source": "cloudflare", "last_status_code": 200, "last_ok": False,
         "last_delivery_age_seconds": 20},
        {"last_source": "cloudflare", "last_status_code": 200, "last_ok": True,
         "last_delivery_age_seconds": 33 * 60},
        {"last_source": "github", "last_status_code": 200, "last_ok": True,
         "last_delivery_age_seconds": 30},
    ],
)
def test_fallback_runs_one_authenticated_three_market_endpoint_cycle(
    status_payload: dict[str, object],
) -> None:
    calls = []

    def fake_open(request, timeout):
        del timeout
        calls.append(request)
        if request.get_method() == "GET":
            return FakeResponse(status_payload)
        return FakeResponse({"ok": True, "processed": 3})

    outcome = run_fallback("https://example.invalid", "server-secret", opener=fake_open)
    assert outcome == "executed"
    assert [request.get_method() for request in calls] == ["GET", "POST"]
    assert calls[-1].full_url == "https://example.invalid/internal/paper-cycle"
    assert calls[-1].get_header("Authorization") == "Bearer server-secret"
    assert calls[-1].get_header("X-scheduler-source") == "github"
    assert not any("postgres" in request.full_url for request in calls)


def test_fallback_runs_after_scheduler_telemetry_failure() -> None:
    calls = []

    def fake_open(request, timeout):
        del timeout
        calls.append(request.get_method())
        if request.get_method() == "GET":
            raise URLError("do not log internal credentials")
        return FakeResponse({"ok": True})

    assert run_fallback(
        "https://example.invalid", "server-secret", opener=fake_open
    ) == "executed"
    assert calls == ["GET", "POST"]


def test_fallback_rejects_missing_token_without_network() -> None:
    with pytest.raises(FallbackFailure, match="repository secret is required"):
        run_fallback("https://example.invalid", "")


def test_fallback_reports_sanitized_http_failure() -> None:
    def fake_open(request, timeout):
        del timeout
        if request.get_method() == "GET":
            return FakeResponse({})
        raise HTTPError(
            request.full_url, 503, "postgresql://secret:pw@host/private", None, None
        )

    with pytest.raises(FallbackFailure) as error:
        run_fallback("https://example.invalid", "server-secret", opener=fake_open)
    assert str(error.value) == "paper cycle endpoint returned HTTP 503"
    assert "server-secret" not in str(error.value)


def test_fallback_fails_closed_when_paper_cycle_has_partial_market_failure() -> None:
    def fake_open(request, timeout):
        del timeout
        if request.get_method() == "GET":
            return FakeResponse({})
        return FakeResponse({"ok": False, "partial_failure": True})

    with pytest.raises(FallbackFailure, match="was not successful"):
        run_fallback("https://example.invalid", "server-secret", opener=fake_open)


def test_fallback_rejects_malformed_and_future_scheduler_ages() -> None:
    for age in (-1, float("nan"), float("inf"), True, "1"):
        assert not _recent_cloudflare({
            "last_source": "cloudflare",
            "last_status_code": 200,
            "last_ok": True,
            "last_delivery_age_seconds": age,
        })

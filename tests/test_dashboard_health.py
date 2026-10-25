from __future__ import annotations

import json
import socket
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path
from threading import Thread
from urllib.error import HTTPError, URLError
from urllib.request import urlopen

import pytest

from ai_trading.dashboard import render_dashboard, serve_dashboard
from ai_trading.deployment_probe import probe_dashboard
from ai_trading.forward_paper_signal import (
    build_forward_paper_observation,
    verify_forward_paper_archive,
)
from ai_trading.hosted_runtime import HostedPaperSettings
from ai_trading.runtime_state import RuntimeStateStore
from ai_trading.runtime_status import HostedRuntimeStatus, HostedRuntimeStatusStore
from ai_trading.trade_journal import TradeJournal


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _get(url: str) -> tuple[int, str, str]:
    try:
        with urlopen(url, timeout=2) as response:
            return (
                response.status,
                response.headers.get("Content-Type", ""),
                response.read().decode(),
            )
    except HTTPError as exc:
        return exc.code, exc.headers.get("Content-Type", ""), exc.read().decode()


def _start_dashboard(
    tmp_path, *, settings: HostedPaperSettings | None = None
) -> int:
    port = _free_port()
    thread = Thread(
        target=serve_dashboard,
        kwargs={
            "journal_path": tmp_path / "trades.jsonl",
            "host": "127.0.0.1",
            "port": port,
            "state_path": tmp_path / "runtime_state.json",
            "status_path": tmp_path / "runtime_status.json",
            "settings": settings,
        },
        daemon=True,
    )
    thread.start()
    deadline = time.time() + 3
    while time.time() < deadline:
        try:
            status, _, _ = _get(f"http://127.0.0.1:{port}/")
            if status == 200:
                return port
        except URLError:
            time.sleep(0.02)
    raise AssertionError("dashboard server did not start")


def test_dashboard_marks_expired_worker_heartbeat_stale(tmp_path) -> None:
    journal = TradeJournal(tmp_path / "trades.jsonl")
    state_store = RuntimeStateStore(tmp_path / "runtime_state.json")
    status_store = HostedRuntimeStatusStore(tmp_path / "runtime_status.json")
    status_store.save(
        HostedRuntimeStatus(
            engine_status="RUNNING",
            symbol="GC=F",
            interval="5m",
            updated_at_utc="2020-01-01T00:00:00+00:00",
            last_cycle_timestamp="2020-01-01T00:00:00+00:00",
            processed=True,
            approved=True,
        )
    )

    page = render_dashboard(
        journal,
        state_store,
        runtime_status_store=status_store,
    )

    assert ">STALE<" in page
    assert "Heartbeat age" in page


def test_api_status_reports_stale_worker_without_hiding_web_health(tmp_path) -> None:
    status_store = HostedRuntimeStatusStore(tmp_path / "runtime_status.json")
    status_store.save(
        HostedRuntimeStatus(
            engine_status="RUNNING",
            symbol="GC=F",
            interval="5m",
            updated_at_utc="2020-01-01T00:00:00+00:00",
        )
    )
    port = _start_dashboard(tmp_path)

    status, content_type, body = _get(f"http://127.0.0.1:{port}/api/status")
    payload = json.loads(body)

    assert status == 200
    assert content_type.startswith("application/json")
    assert payload["engine_status"] == "STALE"
    assert payload["engine_healthy"] is False
    assert payload["heartbeat_age_seconds"] > 0


def test_healthz_keeps_web_liveness_separate_from_engine_health(tmp_path) -> None:
    status_store = HostedRuntimeStatusStore(tmp_path / "runtime_status.json")
    status_store.save(
        HostedRuntimeStatus(
            engine_status="RUNNING",
            symbol="GC=F",
            interval="5m",
            updated_at_utc="2020-01-01T00:00:00+00:00",
        )
    )
    port = _start_dashboard(tmp_path)

    status, content_type, body = _get(f"http://127.0.0.1:{port}/healthz")
    payload = json.loads(body)

    assert status == 200
    assert content_type.startswith("application/json")
    assert payload == {
        "web_healthy": True,
        "engine_healthy": False,
        "engine_status": "STALE",
    }


def test_external_probe_checks_live_ready_and_all_markets(tmp_path, monkeypatch) -> None:
    deployed_sha = "a" * 40
    monkeypatch.setenv("RENDER_GIT_COMMIT", deployed_sha)
    port = _start_dashboard(tmp_path)
    base_url = f"http://127.0.0.1:{port}"
    status, _, body = _get(base_url + "/livez")
    assert status == 200
    assert json.loads(body) == {
        "web_healthy": True,
        "deployed_commit": deployed_sha,
    }

    results = probe_dashboard(base_url, timeout=3, expected_sha=deployed_sha)
    assert [item.endpoint for item in results] == [
        "/livez",
        "/readyz",
        "/api/markets",
    ]
    assert all(item.ok for item in results), results
    assert results[0].detail == "deployed_commit_verified"

    mismatched = probe_dashboard(base_url, timeout=3, expected_sha="b" * 40)
    assert mismatched[0].ok is False
    assert mismatched[0].detail == "deployed_commit_missing_or_mismatched"
    assert all(item.ok for item in mismatched[1:])


def test_external_scheduler_readiness_detects_missing_configuration(
    tmp_path, monkeypatch
) -> None:
    monkeypatch.delenv("AI_TRADING_DATABASE_URL", raising=False)
    monkeypatch.delenv("AI_TRADING_SCHEDULER_TOKEN", raising=False)
    port = _start_dashboard(
        tmp_path,
        settings=HostedPaperSettings(
            enabled=True,
            external_scheduler=True,
            symbol="GC=F",
            period="5d",
            interval="5m",
        ),
    )
    status, _, body = _get(f"http://127.0.0.1:{port}/livez")
    assert status == 200
    assert json.loads(body) == {"web_healthy": True}

    status, _, body = _get(f"http://127.0.0.1:{port}/readyz")
    assert status == 503
    assert json.loads(body) == {
        "ready": False,
        "storage_healthy": True,
        "error": "configuration incomplete",
    }
    readiness = probe_dashboard(f"http://127.0.0.1:{port}", timeout=3)[1]
    assert readiness.ok is False
    assert readiness.detail == "http_503_configuration_incomplete"


def test_render_blueprint_declares_external_runtime_and_secret_inputs() -> None:
    text = Path("render.yaml").read_text(encoding="utf-8")
    for key, value in (
        ("AI_TRADING_HOSTED_PAPER", 'value: "1"'),
        ("AI_TRADING_EXTERNAL_SCHEDULER", 'value: "1"'),
        ("AI_TRADING_HOSTED_INTERVAL", "value: 5m"),
        ("AI_TRADING_DATABASE_URL", "sync: false"),
        ("AI_TRADING_SCHEDULER_TOKEN", "sync: false"),
    ):
        assert f"- key: {key}\n        {value}" in text


def test_external_probe_reports_connection_errors_without_exposing_details(
    monkeypatch
) -> None:
    from urllib.error import URLError

    from ai_trading import deployment_probe

    calls = []

    def fail_request(request, timeout):
        calls.append((request.full_url, timeout))
        raise URLError("private endpoint secret")

    monkeypatch.setattr(deployment_probe, "urlopen", fail_request)
    results = probe_dashboard("https://example.invalid")
    assert len(results) == 3
    assert all(item.ok is False and item.detail == "connection_failed" for item in results)
    # Exactly one short retry per unreachable endpoint, no secret disclosure.
    assert [url.split("/")[-1] for url, _ in calls] == [
        "livez", "readyz", "markets", "livez", "readyz", "markets"
    ]
    assert all(timeout == 10.0 for _, timeout in calls[3:])


def test_probe_rejects_market_cards_with_broken_portfolio(monkeypatch) -> None:
    from io import BytesIO

    from ai_trading import deployment_probe

    class FakeResponse:
        status = 200

        def __init__(self, payload):
            self.body = BytesIO(json.dumps(payload).encode())

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read(self, count):
            return self.body.read(count)

    livez_calls = 0

    def fake_urlopen(request, timeout):
        nonlocal livez_calls
        del timeout
        if request.full_url.endswith("/livez"):
            livez_calls += 1
            if livez_calls == 1:
                raise URLError("transient Render connection reset")
            return FakeResponse({"web_healthy": True})
        if request.full_url.endswith("/readyz"):
            return FakeResponse({"ready": True, "storage_healthy": True})
        return FakeResponse({
            "portfolio": {"equity_complete": False, "error_markets": 1},
            "markets": [
                {"symbol": "GC=F"},
                {"symbol": "^GDAXI"},
                {"symbol": "BTC-USD"},
            ],
        })

    monkeypatch.setattr(deployment_probe, "urlopen", fake_urlopen)
    results = probe_dashboard("https://example.invalid")
    assert results[0].ok is True
    assert livez_calls == 2
    assert results[1].ok is True
    assert results[2].ok is False
    assert results[2].detail == "portfolio_or_market_unavailable"


def test_hosted_probe_requires_running_engines_not_only_complete_portfolio(
    monkeypatch,
) -> None:
    """An all-STARTING service must not pass the production health probe."""
    from io import BytesIO

    from ai_trading import deployment_probe

    statuses = {"GC=F": "STARTING", "^GDAXI": "STARTING", "BTC-USD": "STARTING"}
    cycle_errors = {"GC=F": 0, "^GDAXI": 0, "BTC-USD": 0}

    class FakeResponse:
        status = 200

        def __init__(self, payload):
            self.body = BytesIO(json.dumps(payload).encode())

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read(self, count):
            return self.body.read(count)

    def fake_urlopen(request, timeout):
        del timeout
        if request.full_url.endswith("/livez"):
            return FakeResponse({"web_healthy": True})
        if request.full_url.endswith("/readyz"):
            return FakeResponse({"ready": True, "storage_healthy": True})
        return FakeResponse({
            "portfolio": {
                "equity_complete": True,
                "error_markets": 0,
                "running_markets": sum(s == "RUNNING" for s in statuses.values()),
            },
            "markets": [
                {
                    "symbol": symbol,
                    "overview": {
                        "engine_status": status,
                        "consecutive_cycle_errors": cycle_errors[symbol],
                    },
                }
                for symbol, status in statuses.items()
            ],
        })

    monkeypatch.setattr(deployment_probe, "urlopen", fake_urlopen)
    base = "https://example.invalid"
    cards_only = probe_dashboard(base)
    assert cards_only[2].ok is True  # Backward-compatible card-level check.

    starting = probe_dashboard(base, require_running_markets=True)
    assert starting[0].ok and starting[1].ok
    assert starting[2].ok is False
    assert starting[2].detail == "market_engines_not_running:BTC-USD:STARTING,GC=F:STARTING,^GDAXI:STARTING"

    statuses.update({symbol: "RUNNING" for symbol in statuses})
    healthy = probe_dashboard(base, require_running_markets=True)
    assert healthy[2].ok is True
    assert healthy[2].detail == "three_markets_running"

    cycle_errors["BTC-USD"] = 1
    degraded = probe_dashboard(base, require_running_markets=True)
    assert degraded[2].ok is False
    assert degraded[2].detail == "market_engines_not_running:BTC-USD:RUNNING"

    cycle_errors["BTC-USD"] = 0
    statuses["GC=F"] = "STALE"
    stale = probe_dashboard(base, require_running_markets=True)
    assert stale[2].ok is False
    assert stale[2].detail == "market_engines_not_running:GC=F:STALE"



def test_hosted_probe_rechecks_transient_all_or_some_starting(monkeypatch) -> None:
    from ai_trading import deployment_probe
    from ai_trading.deployment_probe import ProbeCheck

    starting = (
        "market_engines_not_running:"
        "BTC-USD:STARTING,GC=F:STARTING,^GDAXI:STARTING"
    )
    probes = []
    sleeps = []

    def fake_probe(base_url, endpoint, timeout, *, expected_sha, require_running_markets):
        assert base_url == "https://example.invalid"
        assert expected_sha is None
        assert timeout > 0
        assert require_running_markets is True
        probes.append(endpoint)
        if endpoint == "/api/markets":
            market_reads = probes.count("/api/markets")
            if market_reads == 1:
                return ProbeCheck(endpoint, False, starting)
            if market_reads == 2:
                return ProbeCheck(
                    endpoint, False, "market_engines_not_running:BTC-USD:STARTING"
                )
            return ProbeCheck(endpoint, True, "three_markets_running")
        return ProbeCheck(endpoint, True, "healthy")

    monkeypatch.setattr(deployment_probe, "_probe_endpoint", fake_probe)
    monkeypatch.setattr(deployment_probe, "sleep", lambda seconds: sleeps.append(seconds))
    checks = probe_dashboard("https://example.invalid", require_running_markets=True)

    assert all(item.ok for item in checks)
    assert probes == [
        "/livez", "/readyz", "/api/markets", "/api/markets", "/api/markets"
    ]
    assert sleeps == [15.0, 15.0]


def test_hosted_probe_fails_after_bounded_starting_and_never_retries_error(
    monkeypatch,
) -> None:
    from ai_trading import deployment_probe
    from ai_trading.deployment_probe import ProbeCheck

    starting = (
        "market_engines_not_running:"
        "BTC-USD:STARTING,GC=F:STARTING,^GDAXI:STARTING"
    )
    statuses = [starting, "market_engines_not_running:GC=F:ERROR"]
    calls = []
    sleeps = []

    def fake_probe(base_url, endpoint, timeout, *, expected_sha, require_running_markets):
        calls.append(endpoint)
        if endpoint == "/api/markets":
            return ProbeCheck(endpoint, False, statuses[0])
        return ProbeCheck(endpoint, True, "healthy")

    monkeypatch.setattr(deployment_probe, "_probe_endpoint", fake_probe)
    monkeypatch.setattr(deployment_probe, "sleep", lambda seconds: sleeps.append(seconds))
    stuck = probe_dashboard("https://example.invalid", require_running_markets=True)
    assert stuck[-1].ok is False
    assert stuck[-1].detail == starting
    assert calls.count("/api/markets") == 4
    assert sleeps == [15.0, 15.0, 15.0]

    statuses[0] = statuses[1]
    calls.clear()
    sleeps.clear()
    broken = probe_dashboard("https://example.invalid", require_running_markets=True)
    assert broken[-1].detail.endswith("GC=F:ERROR")
    assert calls.count("/api/markets") == 1
    assert sleeps == []


def _forward_observed_market(symbol: str, time: str) -> dict:
    return {
        "symbol": symbol,
        "freshness": "LIVE",
        "session_open": True,
        "signal": "LONG",
        "confidence": 0.72,
        "signal_state": "PAPER_APPROVED",
        "risk_approved": True,
        "signal_time": time,
        "overview": {
            "engine_status": "RUNNING",
            "model": {
                "present": True,
                "format": "joblib-river-v1",
                "version": 1,
                "checksum": "abcdef123456",
            },
        },
    }


def test_forward_paper_signal_timestamp_is_strictly_before_future_entry(tmp_path) -> None:
    now = datetime(2026, 10, 26, 10, 8, tzinfo=UTC)
    data = {
        "markets": [
            _forward_observed_market(symbol, (now - timedelta(minutes=10)).isoformat())
            for symbol in ("GC=F", "^GDAXI", "BTC-USD")
        ]
    }
    record = build_forward_paper_observation(
        data,
        deployed_commit="a" * 40,
        observed_at_utc=now,
        market_response_sha256="b" * 64,
        liveness_response_sha256="c" * 64,
    )
    assert record["eligible_markets"] == 3
    assert record["paper_entry_eligible_markets"] == 3
    assert all(row["paper_entry_eligible"] is True for row in record["markets"])
    assert record["frozen_mtf_comparators_evaluated"] is False
    assert record["orders_or_promotions_executed"] is False
    assert {row["earliest_hypothetical_entry_open_utc"] for row in record["markets"]} == {
        "2026-10-26T10:10:00+00:00"
    }
    path = tmp_path / "observation.json"
    path.write_text(json.dumps(record), encoding="utf-8")
    verify_forward_paper_archive(path)
    record["markets"][0]["paper_entry_eligible"] = False
    path.write_text(json.dumps(record), encoding="utf-8")
    with pytest.raises(ValueError, match="entry eligibility mismatch"):
        verify_forward_paper_archive(path)
    record["markets"][0]["paper_entry_eligible"] = True
    record["markets"][0]["earliest_hypothetical_entry_open_utc"] = now.isoformat()
    path.write_text(json.dumps(record), encoding="utf-8")
    with pytest.raises(ValueError, match="strictly future"):
        verify_forward_paper_archive(path)
    record["observed_at_utc"] = "2027-01-24T00:00:00+00:00"
    path.write_text(json.dumps(record), encoding="utf-8")
    with pytest.raises(ValueError, match="after study window end"):
        verify_forward_paper_archive(path)
    with pytest.raises(ValueError, match="outside preregistered study window"):
        build_forward_paper_observation(
            data, deployed_commit="a" * 40,
            observed_at_utc=datetime(2027, 1, 24, tzinfo=UTC),
            market_response_sha256="b" * 64,
            liveness_response_sha256="c" * 64,
        )


def test_forward_paper_observer_rejects_stale_paper_signals_and_missing_markets(
    tmp_path,
) -> None:
    now = datetime(2026, 10, 26, 10, 8, tzinfo=UTC)
    rows = [
        _forward_observed_market(symbol, (now - timedelta(minutes=10)).isoformat())
        for symbol in ("GC=F", "^GDAXI", "BTC-USD")
    ]
    rows[1]["signal_time"] = (now - timedelta(minutes=45)).isoformat()
    rows[2]["freshness"] = "MARKET_CLOSED"
    rows[2]["session_open"] = False
    record = build_forward_paper_observation(
        {"markets": rows},
        deployed_commit="a" * 40,
        observed_at_utc=now,
        market_response_sha256="b" * 64,
        liveness_response_sha256="c" * 64,
    )
    assert record["eligible_markets"] == 1
    assert record["paper_entry_eligible_markets"] == 1
    assert [row["signal"] for row in record["markets"]] == ["LONG", None, None]
    path = tmp_path / "observation.json"
    path.write_text(json.dumps(record), encoding="utf-8")
    verify_forward_paper_archive(path)

    rows.pop()
    with pytest.raises(ValueError, match="exactly three"):
        build_forward_paper_observation(
            {"markets": rows},
            deployed_commit="a" * 40,
            observed_at_utc=now,
            market_response_sha256="b" * 64,
            liveness_response_sha256="c" * 64,
        )


def test_forward_paper_failed_source_is_auditable_without_fake_forecasts(tmp_path) -> None:
    diagnostic = {
        "schema_version": 1,
        "capture_type": "read_only_paper_river_v1_observation_not_frozen_mtf",
        "status": "source_unavailable",
        "linked_study_start_utc": "2026-10-26T00:00:00+00:00",
        "observed_at_utc": "2026-10-26T10:08:00+00:00",
        "markets": [],
        "eligible_markets": 0,
        "training_or_strategy_selection_performed": False,
        "orders_or_promotions_executed": False,
        "frozen_mtf_comparators_evaluated": False,
        "performance_claim_validated": False,
    }
    path = tmp_path / "observation.json"
    path.write_text(json.dumps(diagnostic), encoding="utf-8")
    verify_forward_paper_archive(path)
    diagnostic["eligible_markets"] = 1
    path.write_text(json.dumps(diagnostic), encoding="utf-8")
    with pytest.raises(ValueError, match="failed forward source evidence"):
        verify_forward_paper_archive(path)


def test_forward_observer_excludes_approved_flat_instead_of_archiving_invalid_signal(
    tmp_path,
) -> None:
    now = datetime(2026, 10, 26, 10, 8, tzinfo=UTC)
    rows = [
        _forward_observed_market(symbol, (now - timedelta(minutes=1)).isoformat())
        for symbol in ("GC=F", "^GDAXI", "BTC-USD")
    ]
    rows[0]["signal_state"] = "PAPER_APPROVED"
    rows[0]["signal"] = "FLAT"
    rows[0]["risk_approved"] = True
    rows[1]["signal_state"] = "NO_TRADE"
    rows[1]["signal"] = "FLAT"
    rows[2]["signal_state"] = "RISK_REJECTED"
    rows[2]["risk_approved"] = False
    record = build_forward_paper_observation(
        {"markets": rows},
        deployed_commit="a" * 40,
        observed_at_utc=now,
        market_response_sha256="b" * 64,
        liveness_response_sha256="c" * 64,
    )
    assert record["eligible_markets"] == 2
    assert record["paper_entry_eligible_markets"] == 0
    assert all(row["paper_entry_eligible"] is False for row in record["markets"])
    assert record["markets"][0]["future_observation_eligible"] is False
    assert record["markets"][0]["signal"] is None
    assert record["markets"][0]["confidence"] is None
    path = tmp_path / "observation.json"
    path.write_text(json.dumps(record), encoding="utf-8")
    verify_forward_paper_archive(path)

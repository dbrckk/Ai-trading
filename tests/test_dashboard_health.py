from __future__ import annotations

import json
import socket
import time
from threading import Thread
from urllib.error import HTTPError, URLError
from urllib.request import urlopen

from ai_trading.dashboard import render_dashboard, serve_dashboard
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


def _start_dashboard(tmp_path) -> int:
    port = _free_port()
    thread = Thread(
        target=serve_dashboard,
        kwargs={
            "journal_path": tmp_path / "trades.jsonl",
            "host": "127.0.0.1",
            "port": port,
            "state_path": tmp_path / "runtime_state.json",
            "status_path": tmp_path / "runtime_status.json",
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

from __future__ import annotations

import json
import socket
import time
from threading import Thread
from urllib.error import URLError
from urllib.request import urlopen

from ai_trading.dashboard import render_dashboard, serve_dashboard
from ai_trading.hosted_runtime import HostedPaperSettings
from ai_trading.persistence import PersistedRuntime
from ai_trading.runtime_state import RuntimeState
from ai_trading.runtime_status import HostedRuntimeStatus
from ai_trading.trade_journal import TradeJournal, TradeSnapshot

RUNTIME_KEY = "paper:GC=F:5m:online-river:v1"


class DurablePersistence:
    def __init__(self) -> None:
        self.state = RuntimeState(
            cash=12_345.0,
            units=2.0,
            last_price=250.0,
            peak_equity=13_000.0,
            day_start_equity=12_500.0,
            processed_bars=7,
        )
        self.trade = TradeSnapshot(
            timestamp_utc="2026-09-15T20:00:00+00:00",
            symbol="GC=F",
            side="BUY",
            quantity=2.0,
            price=250.0,
            status="PAPER_FILLED",
            pnl=25.0,
            confidence=0.8,
            strategy="online-river",
        )
        self.status = HostedRuntimeStatus(
            engine_status="RUNNING",
            symbol="GC=F",
            interval="5m",
            updated_at_utc="2099-01-01T00:00:00+00:00",
            last_cycle_timestamp="2026-09-15T20:00:00+00:00",
            processed=True,
            side=1,
            confidence=0.8,
            approved=True,
            equity=12_845.0,
            units=2.0,
            processed_bars=7,
            poll_seconds=120.0,
        )

    def load_runtime(self, runtime_key: str, starting_cash: float) -> PersistedRuntime:
        assert runtime_key == RUNTIME_KEY
        assert starting_cash == 100_000.0
        return PersistedRuntime(state=self.state, model=None, revision=7, is_new=False)

    def list_trades(self, runtime_key: str | None = None, *, limit: int | None = None):
        assert runtime_key == RUNTIME_KEY
        assert limit == 200
        return (self.trade,)

    def load_runtime_status(self, runtime_key: str) -> HostedRuntimeStatus | None:
        assert runtime_key == RUNTIME_KEY
        return self.status


class FailingPersistence:
    def _fail(self):
        raise RuntimeError("postgresql://user:secret@example.invalid/private")

    def load_runtime(self, runtime_key: str, starting_cash: float):
        del runtime_key, starting_cash
        return self._fail()

    def list_trades(self, runtime_key: str | None = None, *, limit: int | None = None):
        del runtime_key, limit
        return self._fail()

    def load_runtime_status(self, runtime_key: str):
        del runtime_key
        return self._fail()


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _get(url: str) -> tuple[int, str]:
    with urlopen(url, timeout=2) as response:
        return response.status, response.read().decode()


def _start_failure_dashboard() -> int:
    port = _free_port()
    thread = Thread(
        target=serve_dashboard,
        kwargs={
            "host": "127.0.0.1",
            "port": port,
            "persistence": FailingPersistence(),
            "settings": HostedPaperSettings(
                enabled=False,
                symbol="GC=F",
                interval="5m",
            ),
        },
        daemon=True,
    )
    thread.start()
    deadline = time.time() + 3
    while time.time() < deadline:
        try:
            status, _ = _get(f"http://127.0.0.1:{port}/healthz")
            if status == 200:
                return port
        except URLError:
            time.sleep(0.02)
    raise AssertionError("dashboard server did not start")


def test_dashboard_uses_durable_state_trades_and_status(tmp_path) -> None:
    journal = TradeJournal(tmp_path / "empty.jsonl")

    page = render_dashboard(
        journal,
        persistence=DurablePersistence(),
        runtime_key=RUNTIME_KEY,
    )

    assert "12,845.00" in page
    assert "12,345.00" in page
    assert "PAPER_FILLED" in page
    assert "80.0%" in page
    assert ">RUNNING<" in page


def test_dashboard_storage_failure_is_sanitized(tmp_path) -> None:
    page = render_dashboard(
        TradeJournal(tmp_path / "empty.jsonl"),
        persistence=FailingPersistence(),
        runtime_key=RUNTIME_KEY,
    )

    assert "storage unavailable" in page
    assert "100,000.00" not in page
    assert "secret" not in page


def test_status_endpoints_fail_closed_without_leaking_storage_details() -> None:
    port = _start_failure_dashboard()

    status_code, status_body = _get(f"http://127.0.0.1:{port}/api/status")
    health_code, health_body = _get(f"http://127.0.0.1:{port}/healthz")
    status_payload = json.loads(status_body)
    health_payload = json.loads(health_body)

    assert status_code == 200
    assert status_payload == {
        "engine_status": "ERROR",
        "engine_healthy": False,
        "storage_healthy": False,
        "error": "storage unavailable",
    }
    assert "secret" not in status_body
    assert health_code == 200
    assert health_payload == {
        "web_healthy": True,
        "engine_healthy": False,
        "engine_status": "ERROR",
        "storage_healthy": False,
        "error": "storage unavailable",
    }
    assert "secret" not in health_body

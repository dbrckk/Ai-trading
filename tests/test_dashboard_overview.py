from __future__ import annotations

import json
import socket
import time
from threading import Thread
from urllib.error import URLError
from urllib.request import urlopen

from ai_trading.dashboard import serve_dashboard
from ai_trading.hosted_runtime import HostedPaperSettings
from ai_trading.persistence import ModelBlob, PersistedRuntime
from ai_trading.runtime_state import RuntimeState
from ai_trading.runtime_status import HostedRuntimeStatus

RUNTIME_KEY = "paper:GC=F:5m:online-river:v1"


class OverviewPersistence:
    def __init__(self) -> None:
        self.state = RuntimeState(
            cash=12_345.0,
            units=2.0,
            last_price=250.0,
            peak_equity=13_000.0,
            day_start_equity=12_500.0,
            last_processed="2026-09-16T20:45:00+00:00",
            processed_bars=42,
        )
        self.model = ModelBlob(
            format="joblib",
            version=3,
            payload=b"model",
            sha256="1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef",
        )
        self.status = HostedRuntimeStatus(
            engine_status="RUNNING",
            symbol="GC=F",
            interval="5m",
            updated_at_utc="2099-01-01T00:00:00+00:00",
            last_cycle_timestamp="2026-09-16T20:45:00+00:00",
            processed=True,
            side=1,
            confidence=0.8,
            approved=True,
            equity=12_845.0,
            units=2.0,
            processed_bars=42,
            poll_seconds=300.0,
        )

    def load_runtime(self, runtime_key: str, starting_cash: float) -> PersistedRuntime:
        assert runtime_key == RUNTIME_KEY
        assert starting_cash == 100_000.0
        return PersistedRuntime(
            state=self.state,
            model=self.model,
            revision=17,
            is_new=False,
        )

    def list_trades(self, runtime_key: str | None = None, *, limit: int | None = None):
        del runtime_key, limit
        return ()

    def load_runtime_status(self, runtime_key: str) -> HostedRuntimeStatus | None:
        assert runtime_key == RUNTIME_KEY
        return self.status


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _get_json(url: str) -> tuple[int, dict[str, object]]:
    with urlopen(url, timeout=2) as response:
        return response.status, json.loads(response.read().decode())


def _start_dashboard(persistence: OverviewPersistence) -> int:
    port = _free_port()
    thread = Thread(
        target=serve_dashboard,
        kwargs={
            "host": "127.0.0.1",
            "port": port,
            "persistence": persistence,
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
            status, _ = _get_json(f"http://127.0.0.1:{port}/api/status")
            if status == 200:
                return port
        except URLError:
            time.sleep(0.02)
    raise AssertionError("dashboard server did not start")


def test_overview_endpoint_exposes_model_and_runtime_sync_state() -> None:
    port = _start_dashboard(OverviewPersistence())

    status_code, payload = _get_json(f"http://127.0.0.1:{port}/api/overview")

    assert status_code == 200
    assert payload["runtime"] == {
        "revision": 17,
        "is_new": False,
        "processed_bars": 42,
        "last_processed": "2026-09-16T20:45:00+00:00",
        "consistent": True,
    }
    assert payload["model"] == {
        "present": True,
        "format": "joblib",
        "version": 3,
        "sha256_short": "1234567890ab",
    }
    assert payload["sync"] == {
        "engine_status": "RUNNING",
        "lag_detected": False,
    }
    assert payload["alerts"] == []

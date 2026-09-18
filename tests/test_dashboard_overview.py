from __future__ import annotations

import json
import socket
import time
from threading import Thread
from urllib.error import URLError
from urllib.request import urlopen

from ai_trading.burnin import BurnInSnapshot
from ai_trading.dashboard import render_dashboard, serve_dashboard
from ai_trading.hosted_runtime import HostedPaperSettings
from ai_trading.operational_overview import build_operational_overview
from ai_trading.persistence import ModelBlob, PersistedRuntime
from ai_trading.runtime_state import RuntimeState
from ai_trading.runtime_status import HostedRuntimeStatus
from ai_trading.trade_journal import TradeJournal

RUNTIME_KEY = "paper:GC=F:5m:online-river:v1"


class OverviewPersistence:
    def __init__(self, *, with_model: bool = True, stale: bool = False) -> None:
        self.runtime = PersistedRuntime(
            state=RuntimeState(
                cash=12_345.0,
                units=2.0,
                last_price=250.0,
                peak_equity=13_000.0,
                day_start_equity=12_500.0,
                last_processed="2026-09-16 05:20:00+00:00",
                processed_bars=7,
            ),
            model=(
                ModelBlob(
                    format="joblib",
                    version=1,
                    payload=b"model",
                    sha256="1234567890abcdef1234567890abcdef",
                )
                if with_model
                else None
            ),
            revision=7,
            is_new=False,
        )
        self.status = HostedRuntimeStatus(
            engine_status="STALE" if stale else "RUNNING",
            symbol="GC=F",
            interval="5m",
            updated_at_utc="2099-01-01T00:00:00+00:00",
            last_cycle_timestamp="2026-09-16T05:25:00+00:00",
            processed=True,
            side=1,
            confidence=0.8,
            approved=True,
            equity=12_845.0,
            units=2.0,
            processed_bars=7,
            poll_seconds=300.0,
        )

    def load_runtime(self, runtime_key: str, starting_cash: float) -> PersistedRuntime:
        assert runtime_key == RUNTIME_KEY
        assert starting_cash == 100_000.0
        return self.runtime

    def list_trades(self, runtime_key: str | None = None, *, limit: int | None = None):
        assert runtime_key == RUNTIME_KEY
        assert limit == 200
        return ()

    def list_burnin_snapshots(self, runtime_key: str):
        assert runtime_key == RUNTIME_KEY
        return (
            BurnInSnapshot(
                timestamp_utc="2026-09-16T05:15:00+00:00",
                equity=12_500.0,
                scheduler_errors=0,
                regimes_covered=0,
                bootstrap_probability_positive=0.0,
                processed_bars=6,
            ),
            BurnInSnapshot(
                timestamp_utc="2026-09-16T05:20:00+00:00",
                equity=12_845.0,
                scheduler_errors=0,
                regimes_covered=0,
                bootstrap_probability_positive=0.0,
                processed_bars=7,
            ),
        )

    def load_runtime_status(self, runtime_key: str) -> HostedRuntimeStatus | None:
        assert runtime_key == RUNTIME_KEY
        return self.status


class FailingOverviewPersistence:
    def load_runtime(self, runtime_key: str, starting_cash: float):
        del runtime_key, starting_cash
        raise RuntimeError("postgresql://user:secret@example.invalid/private")

    def load_runtime_status(self, runtime_key: str):
        del runtime_key
        raise RuntimeError("postgresql://user:secret@example.invalid/private")


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _start_overview_dashboard(persistence: OverviewPersistence) -> int:
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
            with urlopen(f"http://127.0.0.1:{port}/healthz", timeout=2) as response:
                if response.status == 200:
                    return port
        except URLError:
            time.sleep(0.02)
    raise AssertionError("dashboard server did not start")


def test_operational_overview_exposes_model_and_runtime_metadata() -> None:
    payload = build_operational_overview(OverviewPersistence(), RUNTIME_KEY)

    assert payload["storage_healthy"] is True
    assert payload["runtime_revision"] == 7
    assert payload["processed_bars"] == 7
    assert payload["last_processed"] == "2026-09-16 05:20:00+00:00"
    assert payload["model"] == {
        "present": True,
        "format": "joblib",
        "version": 1,
        "checksum": "1234567890ab",
    }
    assert payload["lag_detected"] is False
    assert payload["burnin"]["samples"] == 2
    assert payload["burnin"]["processed_bars"] == 7
    assert payload["burnin"]["total_return"] > 0.0
    assert payload["burnin"]["max_drawdown"] == 0.0
    assert payload["alerts"] == []


def test_operational_overview_flags_stale_runtime() -> None:
    payload = build_operational_overview(
        OverviewPersistence(stale=True),
        RUNTIME_KEY,
    )

    assert payload["lag_detected"] is True
    assert payload["alerts"] == ["worker heartbeat expired"]


def test_operational_overview_flags_missing_model_after_processing() -> None:
    payload = build_operational_overview(
        OverviewPersistence(with_model=False),
        RUNTIME_KEY,
    )

    assert payload["model"] == {
        "present": False,
        "format": None,
        "version": None,
        "checksum": None,
    }
    assert payload["alerts"] == ["model missing for initialized runtime"]


def test_operational_overview_flags_inconsistent_runtime() -> None:
    persistence = OverviewPersistence()
    persistence.runtime = PersistedRuntime(
        state=RuntimeState(
            cash=12_345.0,
            units=2.0,
            last_price=250.0,
            peak_equity=13_000.0,
            day_start_equity=12_500.0,
            last_processed=None,
            processed_bars=7,
        ),
        model=persistence.runtime.model,
        revision=7,
        is_new=False,
    )

    payload = build_operational_overview(persistence, RUNTIME_KEY)

    assert payload["alerts"] == ["runtime inconsistent"]


def test_operational_overview_storage_failure_is_sanitized() -> None:
    payload = build_operational_overview(FailingOverviewPersistence(), RUNTIME_KEY)

    assert payload == {
        "storage_healthy": False,
        "engine_status": "ERROR",
        "runtime_revision": None,
        "processed_bars": None,
        "last_processed": None,
        "lag_detected": False,
        "model": {
            "present": False,
            "format": None,
            "version": None,
            "checksum": None,
        },
        "burnin": {
            "samples": 0,
            "processed_bars": 0,
            "total_return": None,
            "max_drawdown": None,
        },
        "alerts": ["storage unavailable"],
    }
    assert "secret" not in repr(payload)
    assert "example.invalid" not in repr(payload)


def test_dashboard_exposes_operational_overview_endpoint() -> None:
    port = _start_overview_dashboard(OverviewPersistence())

    with urlopen(f"http://127.0.0.1:{port}/api/overview", timeout=2) as response:
        payload = json.loads(response.read().decode())

    assert response.status == 200
    assert payload["runtime_revision"] == 7
    assert payload["model"]["present"] is True
    assert payload["model"]["checksum"] == "1234567890ab"
    assert payload["burnin"]["processed_bars"] == 7
    assert payload["burnin"]["samples"] == 2
    assert payload["alerts"] == []


def test_dashboard_renders_model_and_revision_metadata(tmp_path) -> None:
    page = render_dashboard(
        TradeJournal(tmp_path / "empty.jsonl"),
        persistence=OverviewPersistence(),
        runtime_key=RUNTIME_KEY,
    )

    assert '<small>Runtime revision</small><strong>7</strong>' in page
    assert '<small>Model</small><strong>joblib v1</strong>' in page
    assert '<small>Model checksum</small><strong>1234567890ab</strong>' in page
    assert "Operational alerts: none" in page


def test_dashboard_renders_operational_alerts(tmp_path) -> None:
    page = render_dashboard(
        TradeJournal(tmp_path / "empty.jsonl"),
        persistence=OverviewPersistence(with_model=False, stale=True),
        runtime_key=RUNTIME_KEY,
    )

    assert "Operational alerts: worker heartbeat expired · model missing for initialized runtime" in page


def test_dashboard_renders_inconsistent_runtime_alert(tmp_path) -> None:
    persistence = OverviewPersistence()
    persistence.runtime = PersistedRuntime(
        state=RuntimeState(
            cash=12_345.0,
            units=2.0,
            last_price=250.0,
            peak_equity=13_000.0,
            day_start_equity=12_500.0,
            last_processed=None,
            processed_bars=7,
        ),
        model=persistence.runtime.model,
        revision=7,
        is_new=False,
    )

    page = render_dashboard(
        TradeJournal(tmp_path / "empty.jsonl"),
        persistence=persistence,
        runtime_key=RUNTIME_KEY,
    )

    assert "Operational alerts: runtime inconsistent" in page

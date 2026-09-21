from __future__ import annotations

import json
import socket
import time
from threading import Thread
from urllib.error import HTTPError, URLError
from urllib.request import urlopen

from ai_trading.burnin import BurnInSnapshot
from ai_trading.dashboard import render_dashboard, serve_dashboard
from ai_trading.hosted_runtime import HostedPaperSettings
from ai_trading.performance_metrics import performance_metrics_from_totals
from ai_trading.persistence import PersistedRuntime, SchedulerDelivery
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
            last_processed="2026-09-16 05:20:00+00:00",
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

    def load_trade_performance(self, runtime_key: str):
        assert runtime_key == RUNTIME_KEY
        return performance_metrics_from_totals(
            trade_count=250,
            realized_pnl=375.0,
            gross_profit=500.0,
            gross_loss=125.0,
            max_drawdown=80.0,
        )

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

    def list_regimes(self, runtime_key: str) -> tuple[str, ...]:
        assert runtime_key == RUNTIME_KEY
        return ("bull_normal_vol", "sideways_normal_vol")

    def load_runtime_status(self, runtime_key: str) -> HostedRuntimeStatus | None:
        assert runtime_key == RUNTIME_KEY
        return self.status

    def list_scheduler_deliveries(self, *, limit: int = 20):
        assert limit == 20
        return tuple(
            SchedulerDelivery(
                timestamp_utc=f"2026-09-21T16:{minute:02d}:00+00:00",
                source="cloudflare",
                status_code=200,
                ok=True,
                processed=1,
            )
            for minute in (0, 5, 10)
        )


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
    try:
        with urlopen(url, timeout=2) as response:
            return response.status, response.read().decode()
    except HTTPError as exc:
        return exc.code, exc.read().decode()


def _get_with_headers(url: str):
    with urlopen(url, timeout=2) as response:
        return response.status, response.headers, response.read().decode()


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
    assert "Last processed" in page
    assert "2026-09-16 05:20:00+00:00" in page
    assert "Processed bars" in page
    assert ">7<" in page
    assert '<small>Trades</small><strong>250</strong>' in page
    assert '<small>Realized PnL</small><strong>375.00</strong>' in page
    assert '<small>Avg PnL / observed</small><strong>1.50</strong>' in page
    assert '<small>PnL coverage</small><strong>250 / 250</strong>' in page
    assert '<small>Profit factor</small><strong>4.00</strong>' in page
    assert '<small>Max realized DD</small><strong>80.00</strong>' in page
    assert "Performance window: full persisted history" in page
    assert '<small>Burn-in bars</small><strong>7 / 126</strong>' in page
    assert '<small>Burn-in progress</small><strong>6%</strong>' in page
    assert '<small>Equity return</small><strong>2.76%</strong>' in page
    assert '<small>Equity max DD</small><strong>0.00%</strong>' in page


def test_dashboard_storage_failure_is_sanitized(tmp_path) -> None:
    page = render_dashboard(
        TradeJournal(tmp_path / "empty.jsonl"),
        persistence=FailingPersistence(),
        runtime_key=RUNTIME_KEY,
    )

    assert "storage unavailable" in page
    assert "100,000.00" not in page
    assert "secret" not in page
    assert "example.invalid" not in page


def test_liveness_stays_healthy_when_storage_is_unavailable() -> None:
    port = _start_failure_dashboard()

    status_code, body = _get(f"http://127.0.0.1:{port}/livez")

    assert status_code == 200
    assert json.loads(body) == {"web_healthy": True}


def test_readiness_fails_when_durable_storage_is_unavailable() -> None:
    port = _start_failure_dashboard()

    status_code, body = _get(f"http://127.0.0.1:{port}/readyz")

    assert status_code == 503
    assert json.loads(body) == {
        "ready": False,
        "storage_healthy": False,
        "error": "storage unavailable",
    }
    assert "secret" not in body
    assert "example.invalid" not in body


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
    assert "example.invalid" not in status_body
    assert health_code == 200
    assert health_payload == {
        "web_healthy": True,
        "engine_healthy": False,
        "engine_status": "ERROR",
        "storage_healthy": False,
        "error": "storage unavailable",
    }
    assert "secret" not in health_body
    assert "example.invalid" not in health_body


def test_dashboard_surfaces_verified_scheduler_delivery(tmp_path) -> None:
    page = render_dashboard(
        TradeJournal(tmp_path / "empty.jsonl"),
        persistence=DurablePersistence(),
        runtime_key=RUNTIME_KEY,
    )

    assert 'href="#scheduler"' in page
    assert 'id="scheduler"' in page
    assert "Scheduler delivery" in page
    assert "VERIFIED" in page
    assert "3 / 3" in page
    assert "cloudflare" in page
    assert "2026-09-21T16:10:00+00:00" in page
    assert "Authentication material is never persisted or displayed." in page


def test_dashboard_http_responses_include_security_headers() -> None:
    port = _start_failure_dashboard()
    status, headers, _ = _get_with_headers(f"http://127.0.0.1:{port}/healthz")

    assert status == 200
    assert headers["X-Content-Type-Options"] == "nosniff"
    assert headers["X-Frame-Options"] == "DENY"
    assert headers["Referrer-Policy"] == "no-referrer"
    assert headers["Permissions-Policy"] == "camera=(), microphone=(), geolocation=()"
    assert "frame-ancestors 'none'" in headers["Content-Security-Policy"]
    assert "Python" not in headers["Server"]


def test_dashboard_v2_groups_critical_sections_and_renders_equity_chart(tmp_path) -> None:
    page = render_dashboard(
        TradeJournal(tmp_path / "empty.jsonl"),
        persistence=DurablePersistence(),
        runtime_key=RUNTIME_KEY,
    )

    assert "System health" in page
    assert "Trading state" in page
    assert "Performance" in page
    assert "Burn-in evidence" in page
    assert 'class="status-badge status-warn"' in page
    assert 'class="equity-chart"' in page
    assert "<svg" in page
    assert "<polyline" in page
    assert 'class="table-scroll"' in page


def test_dashboard_premium_shell_and_navigation(tmp_path) -> None:
    page = render_dashboard(
        TradeJournal(tmp_path / "empty.jsonl"),
        persistence=DurablePersistence(),
        runtime_key=RUNTIME_KEY,
    )

    assert 'class="premium-shell"' in page
    assert 'class="top-nav"' in page
    assert 'href="#overview"' in page
    assert 'href="#performance"' in page
    assert 'href="#burnin"' in page
    assert 'href="#trades"' in page
    assert 'class="hero-kpis"' in page
    assert 'class="live-dot"' in page
    assert 'class="chart-area ' in page
    assert "AI Trading Terminal" in page


def test_dashboard_quant_evidence_is_explicit_and_non_misleading(tmp_path) -> None:
    page = render_dashboard(
        TradeJournal(tmp_path / "empty.jsonl"),
        persistence=DurablePersistence(),
        runtime_key=RUNTIME_KEY,
    )

    assert "Quant evidence" in page
    assert "Bootstrap positive probability" in page
    assert "Scheduler reliability" in page
    assert "Regime coverage" in page
    assert '<small>Regime coverage</small><strong>2 / 2</strong>' in page
    assert "Observed regimes: bull_normal_vol · sideways_normal_vol." in page
    assert "not yet persisted" not in page
    assert "Sharpe" in page
    assert "Sortino" in page
    assert "Full readiness" in page
    assert "Readiness checks" in page
    assert "pending interval-aware annualization" not in page


class ReadinessPersistence(DurablePersistence):
    def list_burnin_snapshots(self, runtime_key: str):
        assert runtime_key == RUNTIME_KEY
        return (
            BurnInSnapshot(
                timestamp_utc="2026-09-16T05:10:00+00:00",
                equity=12_000.0,
                scheduler_errors=0,
                regimes_covered=2,
                bootstrap_probability_positive=0.0,
                processed_bars=5,
            ),
            BurnInSnapshot(
                timestamp_utc="2026-09-16T05:15:00+00:00",
                equity=12_400.0,
                scheduler_errors=0,
                regimes_covered=2,
                bootstrap_probability_positive=0.0,
                processed_bars=6,
            ),
            BurnInSnapshot(
                timestamp_utc="2026-09-16T05:20:00+00:00",
                equity=12_845.0,
                scheduler_errors=0,
                regimes_covered=2,
                bootstrap_probability_positive=0.0,
                processed_bars=7,
            ),
        )


def test_dashboard_readiness_panel_shows_eight_criteria_with_thresholds(tmp_path) -> None:
    page = render_dashboard(
        TradeJournal(tmp_path / "empty.jsonl"),
        persistence=ReadinessPersistence(),
        runtime_key=RUNTIME_KEY,
    )

    assert 'class="readiness-grid"' in page
    assert page.count('class="readiness-row"') == 8
    for label in (
        "Burn-in bars",
        "Sharpe",
        "Sortino",
        "Max drawdown",
        "Total return",
        "Bootstrap confidence",
        "Regime coverage",
        "Scheduler errors",
    ):
        assert label in page
    assert "PASS" in page
    assert "FAIL" in page
    assert "&gt;=" in page or ">=" in page
    assert "&lt;=" in page or "<=" in page

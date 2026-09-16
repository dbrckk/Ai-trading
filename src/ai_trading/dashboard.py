from __future__ import annotations

import html
import json
import os
from collections.abc import Callable
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

from .file_persistence import FilePaperPersistence
from .hosted_runtime import HostedPaperSettings, start_hosted_paper_runtime
from .operational_overview import build_operational_overview
from .paper_cycle import PaperCycleResult
from .paper_cycle_service import (
    ProductionPaperCycleSettings,
    run_production_paper_cycle,
)
from .persistence import PaperPersistence
from .persistence_factory import build_paper_persistence
from .runtime_state import RuntimeStateStore
from .runtime_status import HostedRuntimeStatus, HostedRuntimeStatusStore, runtime_status_snapshot
from .scheduler_endpoint import handle_scheduler_request
from .trade_journal import TradeJournal

_STORAGE_ERROR_STATUS: dict[str, object] = {
    "engine_status": "ERROR",
    "engine_healthy": False,
    "storage_healthy": False,
    "error": "storage unavailable",
}

_STORAGE_ERROR_OVERVIEW: dict[str, object] = {
    "runtime": {
        "revision": None,
        "is_new": None,
        "processed_bars": None,
        "last_processed": None,
        "consistent": False,
    },
    "model": {
        "present": False,
        "format": None,
        "version": None,
        "sha256_short": None,
    },
    "sync": {
        "engine_status": "ERROR",
        "lag_detected": True,
    },
    "alerts": ["storage unavailable"],
}


def _public_runtime_snapshot(status: HostedRuntimeStatus | None) -> dict[str, object]:
    snapshot = runtime_status_snapshot(status)
    if snapshot.get("error"):
        snapshot["error"] = "worker failure"
    return snapshot


def _display_money(value: float | None) -> str:
    return "-" if value is None else f"{value:,.2f}"


def _display_units(value: float | None) -> str:
    return "-" if value is None else f"{value:g}"


def render_dashboard(
    journal: TradeJournal,
    state_store: RuntimeStateStore | None = None,
    starting_cash: float = 100_000.0,
    *,
    runtime_status_store: HostedRuntimeStatusStore | None = None,
    persistence: PaperPersistence | None = None,
    runtime_key: str | None = None,
) -> str:
    storage_error = False
    if persistence is not None and runtime_key is not None:
        try:
            recent = persistence.list_trades(runtime_key, limit=200)
            persisted = persistence.load_runtime(runtime_key, starting_cash)
            state = persisted.state
            runtime_status = persistence.load_runtime_status(runtime_key)
        except Exception:
            recent = ()
            state = None
            runtime_status = None
            storage_error = True
    else:
        recent = journal.list(limit=200)
        state = state_store.load(starting_cash) if state_store is not None else None
        runtime_status = (
            runtime_status_store.load() if runtime_status_store is not None else None
        )

    trades = reversed(recent)
    if storage_error:
        realized_pnl: float | None = None
        trade_count: int | None = None
        wins: int | None = None
        losses: int | None = None
        win_rate: float | None = None
        active_symbols: int | None = None
        cash: float | None = None
        units: float | None = None
        equity: float | None = None
        position_value: float | None = None
    else:
        realized_pnl = sum(trade.pnl for trade in recent)
        trade_count = len(recent)
        wins = sum(1 for trade in recent if trade.pnl > 0)
        losses = sum(1 for trade in recent if trade.pnl < 0)
        win_rate = (wins / (wins + losses)) if wins + losses else 0.0
        active_symbols = len({trade.symbol for trade in recent})
        cash = state.cash if state is not None else starting_cash
        units = state.units if state is not None else 0.0
        last_price = state.last_price if state is not None else 0.0
        equity = state.cash + state.units * state.last_price if state is not None else starting_cash
        position_value = units * last_price

    last_processed = (
        state.last_processed
        if state is not None and state.last_processed and not storage_error
        else "-"
    )
    processed_bars_display = (
        str(state.processed_bars) if state is not None and not storage_error else "-"
    )

    runtime_snapshot = _public_runtime_snapshot(runtime_status)
    engine_status = "ERROR" if storage_error else str(runtime_snapshot["engine_status"])
    market = (
        f"{runtime_status.symbol} · {runtime_status.interval}"
        if runtime_status is not None and not storage_error
        else "-"
    )
    last_cycle = (
        runtime_status.last_cycle_timestamp
        if runtime_status is not None
        and runtime_status.last_cycle_timestamp
        and not storage_error
        else "-"
    )
    last_heartbeat = (
        runtime_status.updated_at_utc
        if runtime_status is not None and not storage_error
        else "-"
    )
    heartbeat_age_value = None if storage_error else runtime_snapshot["heartbeat_age_seconds"]
    heartbeat_age = (
        "-" if heartbeat_age_value is None else f"{float(heartbeat_age_value):.0f}s"
    )
    signal = "-"
    confidence = "-"
    risk_decision = "-"
    decision_reason = "storage unavailable" if storage_error else "-"
    if runtime_status is not None and not storage_error:
        decision_reason = (
            "worker failure" if runtime_status.error else runtime_status.reason or "-"
        )
        if engine_status == "STALE" and decision_reason == "-":
            decision_reason = "worker heartbeat expired"
        if runtime_status.last_cycle_timestamp is not None:
            if runtime_status.processed:
                signal = {1: "LONG", -1: "SHORT", 0: "FLAT"}.get(
                    runtime_status.side,
                    "UNKNOWN",
                )
                confidence = f"{runtime_status.confidence:.1%}"
                risk_decision = "APPROVED" if runtime_status.approved else "REJECTED"
            else:
                risk_decision = "SKIPPED"

    if storage_error:
        rows = '<tr><td colspan="9">Storage unavailable.</td></tr>'
    else:
        rows = "".join(
            "<tr>"
            f"<td>{html.escape(t.timestamp_utc)}</td>"
            f"<td>{html.escape(t.symbol)}</td>"
            f"<td>{html.escape(t.side)}</td>"
            f"<td>{t.quantity:g}</td>"
            f"<td>{t.price:.4f}</td>"
            f"<td>{html.escape(t.status)}</td>"
            f"<td>{t.pnl:.2f}</td>"
            f"<td>{'-' if t.confidence is None else f'{t.confidence:.1%}'}</td>"
            f"<td>{html.escape(t.strategy)}</td>"
            "</tr>"
            for t in trades
        )
        if not rows:
            rows = '<tr><td colspan="9">No trades recorded yet.</td></tr>'

    trade_count_display = "-" if trade_count is None else str(trade_count)
    pnl_display = _display_money(realized_pnl)
    win_rate_display = "-" if win_rate is None else f"{win_rate:.1%}"
    wins_losses_display = "-" if wins is None or losses is None else f"{wins} / {losses}"
    active_symbols_display = "-" if active_symbols is None else str(active_symbols)

    return f"""<!doctype html>
<html><head><meta charset="utf-8"><meta http-equiv="refresh" content="2">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>AI Trading — Live</title>
<style>
body{{font-family:system-ui;margin:0;background:#0b1020;color:#e8edf7}}
main{{max-width:1400px;margin:auto;padding:24px}} h1{{margin:0 0 8px}}
small{{color:#9aa7bd}} table{{width:100%;border-collapse:collapse;margin-top:24px}}
.metrics{{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:12px;margin-top:18px}}
.metric{{background:#0b1020;border:1px solid #26324a;border-radius:10px;padding:14px}}
.metric strong{{display:block;font-size:1.4rem;margin-top:4px}}
.runtime-reason{{display:block;margin-top:14px}}
th,td{{padding:10px;border-bottom:1px solid #26324a;text-align:right}}
th:first-child,td:first-child,th:nth-child(2),td:nth-child(2),
th:nth-child(3),td:nth-child(3),th:last-child,td:last-child{{text-align:left}}
.card{{background:#121a2d;border:1px solid #26324a;border-radius:12px;padding:18px}}
</style></head><body><main>
<div class="card"><h1>AI Trading — Live trades</h1>
<small>Read-only dashboard · auto refresh 2s · hosted paper runtime</small>
<div class="metrics">
<div class="metric"><small>Engine</small><strong>{html.escape(engine_status)}</strong></div>
<div class="metric"><small>Market</small><strong>{html.escape(market)}</strong></div>
<div class="metric"><small>Last heartbeat</small><strong>{html.escape(last_heartbeat)}</strong></div>
<div class="metric"><small>Heartbeat age</small><strong>{html.escape(heartbeat_age)}</strong></div>
<div class="metric"><small>Last cycle</small><strong>{html.escape(last_cycle)}</strong></div>
<div class="metric"><small>Last processed</small><strong>{html.escape(last_processed)}</strong></div>
<div class="metric"><small>Processed bars</small><strong>{processed_bars_display}</strong></div>
<div class="metric"><small>Signal</small><strong>{html.escape(signal)}</strong></div>
<div class="metric"><small>AI confidence</small><strong>{html.escape(confidence)}</strong></div>
<div class="metric"><small>Risk decision</small><strong>{html.escape(risk_decision)}</strong></div>
<div class="metric"><small>Equity</small><strong>{_display_money(equity)}</strong></div>
<div class="metric"><small>Cash</small><strong>{_display_money(cash)}</strong></div>
<div class="metric"><small>Open units</small><strong>{_display_units(units)}</strong></div>
<div class="metric"><small>Position value</small><strong>{_display_money(position_value)}</strong></div>
<div class="metric"><small>Trades</small><strong>{trade_count_display}</strong></div>
<div class="metric"><small>Realized PnL</small><strong>{pnl_display}</strong></div>
<div class="metric"><small>Win rate</small><strong>{win_rate_display}</strong></div>
<div class="metric"><small>Wins / Losses</small><strong>{wins_losses_display}</strong></div>
<div class="metric"><small>Active symbols</small><strong>{active_symbols_display}</strong></div>
</div>
<small class="runtime-reason">Last engine reason: {html.escape(decision_reason)}</small>
<table><thead><tr><th>UTC</th><th>Symbol</th><th>Side</th><th>Qty</th><th>Price</th>
<th>Status</th><th>PnL</th><th>Confidence</th><th>Strategy</th></tr></thead>
<tbody>{rows}</tbody></table></div></main></body></html>"""


def serve_dashboard(
    journal_path: str | Path = "artifacts/trades.jsonl",
    *,
    host: str = "127.0.0.1",
    port: int = 8765,
    state_path: str | Path = "artifacts/runtime_state.json",
    status_path: str | Path = "artifacts/runtime_status.json",
    starting_cash: float = 100_000.0,
    persistence: PaperPersistence | None = None,
    settings: HostedPaperSettings | None = None,
    scheduler_token: str | None = None,
    paper_cycle_executor: Callable[[], PaperCycleResult] | None = None,
) -> None:
    effective_settings = settings or HostedPaperSettings.from_env()
    journal = TradeJournal(journal_path)
    state_store = RuntimeStateStore(state_path)
    runtime_status_store = HostedRuntimeStatusStore(status_path)

    backend = persistence
    if backend is None:
        if os.getenv("AI_TRADING_DATABASE_URL", "").strip():
            backend = build_paper_persistence()
        else:
            root = Path(state_path).parent
            backend = FilePaperPersistence(
                root=root,
                state_store=state_store,
                trade_journal=journal,
                status_store=runtime_status_store,
                model_path=root / "models" / "online-river.joblib",
            )

    runtime_key = effective_settings.runtime_key
    effective_scheduler_token = (
        scheduler_token
        if scheduler_token is not None
        else os.getenv("AI_TRADING_SCHEDULER_TOKEN", "").strip()
    )
    effective_cycle_executor = paper_cycle_executor
    if effective_cycle_executor is None:
        cycle_settings = ProductionPaperCycleSettings(
            symbol=effective_settings.symbol,
            period=effective_settings.period,
            interval=effective_settings.interval,
            max_catchup_bars=12,
            poll_seconds=300.0,
        )

        def execute_paper_cycle() -> PaperCycleResult:
            return run_production_paper_cycle(
                cycle_settings,
                persistence=backend,
            )

        effective_cycle_executor = execute_paper_cycle

    start_hosted_paper_runtime(
        settings=effective_settings,
        persistence=backend,
    )

    def load_status_snapshot() -> dict[str, object]:
        try:
            return _public_runtime_snapshot(backend.load_runtime_status(runtime_key))
        except Exception:
            return dict(_STORAGE_ERROR_STATUS)

    def load_operational_overview() -> dict[str, object]:
        try:
            persisted = backend.load_runtime(runtime_key, starting_cash)
            status = backend.load_runtime_status(runtime_key)
            return build_operational_overview(persisted, status)
        except Exception:
            return dict(_STORAGE_ERROR_OVERVIEW)

    class Handler(BaseHTTPRequestHandler):
        def _send_json(
            self,
            payload: dict[str, object],
            *,
            status_code: int = 200,
        ) -> None:
            body = json.dumps(payload, sort_keys=True).encode()
            self.send_response(status_code)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self) -> None:
            path = urlsplit(self.path).path.rstrip("/")
            if path == "/api/status":
                self._send_json(load_status_snapshot())
                return
            if path == "/api/overview":
                self._send_json(load_operational_overview())
                return
            if path == "/healthz":
                snapshot = load_status_snapshot()
                if snapshot.get("storage_healthy") is False:
                    self._send_json(
                        {
                            "web_healthy": True,
                            "engine_healthy": False,
                            "engine_status": "ERROR",
                            "storage_healthy": False,
                            "error": "storage unavailable",
                        }
                    )
                else:
                    self._send_json(
                        {
                            "web_healthy": True,
                            "engine_healthy": bool(snapshot["engine_healthy"]),
                            "engine_status": str(snapshot["engine_status"]),
                        }
                    )
                return
            if path not in {"", "/index.html"}:
                self.send_error(404)
                return
            payload = render_dashboard(
                journal,
                state_store,
                starting_cash,
                runtime_status_store=runtime_status_store,
                persistence=backend,
                runtime_key=runtime_key,
            ).encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def do_POST(self) -> None:
            path = urlsplit(self.path).path.rstrip("/")
            if path != "/internal/paper-cycle":
                self.send_error(404)
                return
            response = handle_scheduler_request(
                authorization=self.headers.get("Authorization"),
                configured_token=effective_scheduler_token,
                run_cycle=effective_cycle_executor,
            )
            self._send_json(
                response.payload,
                status_code=response.status_code,
            )

        def log_message(self, format: str, *args: object) -> None:
            return

    ThreadingHTTPServer((host, port), Handler).serve_forever()
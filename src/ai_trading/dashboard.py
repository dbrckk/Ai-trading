from __future__ import annotations

import html
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

from .hosted_runtime import start_hosted_paper_runtime
from .runtime_state import RuntimeStateStore
from .runtime_status import HostedRuntimeStatusStore, runtime_status_snapshot
from .trade_journal import TradeJournal


def render_dashboard(
    journal: TradeJournal,
    state_store: RuntimeStateStore | None = None,
    starting_cash: float = 100_000.0,
    *,
    runtime_status_store: HostedRuntimeStatusStore | None = None,
) -> str:
    recent = journal.list(limit=200)
    trades = reversed(recent)
    realized_pnl = sum(trade.pnl for trade in recent)
    trade_count = len(recent)
    wins = sum(1 for trade in recent if trade.pnl > 0)
    losses = sum(1 for trade in recent if trade.pnl < 0)
    win_rate = (wins / (wins + losses)) if wins + losses else 0.0
    active_symbols = len({trade.symbol for trade in recent})
    state = state_store.load(starting_cash) if state_store is not None else None
    cash = state.cash if state is not None else starting_cash
    units = state.units if state is not None else 0.0
    last_price = state.last_price if state is not None else 0.0
    equity = state.cash + state.units * state.last_price if state is not None else starting_cash
    position_value = units * last_price

    runtime_status = (
        runtime_status_store.load() if runtime_status_store is not None else None
    )
    runtime_snapshot = runtime_status_snapshot(runtime_status)
    engine_status = str(runtime_snapshot["engine_status"])
    market = (
        f"{runtime_status.symbol} · {runtime_status.interval}"
        if runtime_status is not None
        else "-"
    )
    last_cycle = (
        runtime_status.last_cycle_timestamp
        if runtime_status is not None and runtime_status.last_cycle_timestamp
        else "-"
    )
    last_heartbeat = runtime_status.updated_at_utc if runtime_status is not None else "-"
    heartbeat_age_value = runtime_snapshot["heartbeat_age_seconds"]
    heartbeat_age = (
        "-"
        if heartbeat_age_value is None
        else f"{float(heartbeat_age_value):.0f}s"
    )
    signal = "-"
    confidence = "-"
    risk_decision = "-"
    decision_reason = "-"
    if runtime_status is not None:
        decision_reason = runtime_status.error or runtime_status.reason or "-"
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
<div class="metric"><small>Signal</small><strong>{html.escape(signal)}</strong></div>
<div class="metric"><small>AI confidence</small><strong>{html.escape(confidence)}</strong></div>
<div class="metric"><small>Risk decision</small><strong>{html.escape(risk_decision)}</strong></div>
<div class="metric"><small>Equity</small><strong>{equity:,.2f}</strong></div>
<div class="metric"><small>Cash</small><strong>{cash:,.2f}</strong></div>
<div class="metric"><small>Open units</small><strong>{units:g}</strong></div>
<div class="metric"><small>Position value</small><strong>{position_value:,.2f}</strong></div>
<div class="metric"><small>Trades</small><strong>{trade_count}</strong></div>
<div class="metric"><small>Realized PnL</small><strong>{realized_pnl:.2f}</strong></div>
<div class="metric"><small>Win rate</small><strong>{win_rate:.1%}</strong></div>
<div class="metric"><small>Wins / Losses</small><strong>{wins} / {losses}</strong></div>
<div class="metric"><small>Active symbols</small><strong>{active_symbols}</strong></div>
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
) -> None:
    start_hosted_paper_runtime()
    journal = TradeJournal(journal_path)
    state_store = RuntimeStateStore(state_path)
    runtime_status_store = HostedRuntimeStatusStore(status_path)

    class Handler(BaseHTTPRequestHandler):
        def _send_json(self, payload: dict[str, object]) -> None:
            body = json.dumps(payload, sort_keys=True).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self) -> None:
            path = urlsplit(self.path).path.rstrip("/")
            if path == "/api/status":
                self._send_json(runtime_status_snapshot(runtime_status_store.load()))
                return
            if path == "/healthz":
                snapshot = runtime_status_snapshot(runtime_status_store.load())
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
            ).encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def log_message(self, format: str, *args: object) -> None:
            return

    ThreadingHTTPServer((host, port), Handler).serve_forever()

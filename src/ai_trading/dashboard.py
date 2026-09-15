from __future__ import annotations

import html
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from .trade_journal import TradeJournal


def render_dashboard(journal: TradeJournal) -> str:
    trades = reversed(journal.list(limit=200))
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
th,td{{padding:10px;border-bottom:1px solid #26324a;text-align:right}}
th:first-child,td:first-child,th:nth-child(2),td:nth-child(2),
th:nth-child(3),td:nth-child(3),th:last-child,td:last-child{{text-align:left}}
.card{{background:#121a2d;border:1px solid #26324a;border-radius:12px;padding:18px}}
</style></head><body><main>
<div class="card"><h1>AI Trading — Live trades</h1>
<small>Read-only dashboard · auto refresh 2s · paper/live status comes from journal events</small>
<table><thead><tr><th>UTC</th><th>Symbol</th><th>Side</th><th>Qty</th><th>Price</th>
<th>Status</th><th>PnL</th><th>Confidence</th><th>Strategy</th></tr></thead>
<tbody>{rows}</tbody></table></div></main></body></html>"""


def serve_dashboard(
    journal_path: str | Path = "artifacts/trades.jsonl",
    *,
    host: str = "127.0.0.1",
    port: int = 8765,
) -> None:
    journal = TradeJournal(journal_path)

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            if self.path not in {"/", "/index.html"}:
                self.send_error(404)
                return
            payload = render_dashboard(journal).encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def log_message(self, format: str, *args: object) -> None:
            return

    ThreadingHTTPServer((host, port), Handler).serve_forever()

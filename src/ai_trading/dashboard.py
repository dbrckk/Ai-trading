from __future__ import annotations

import html
import json
import os
from collections.abc import Callable
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

from .burnin import BurnInSnapshot, calculate_burnin_metrics
from .file_persistence import FilePaperPersistence
from .hosted_runtime import HostedPaperSettings, start_hosted_paper_runtime
from .multi_market import (
    MarketSpec,
    build_multi_market_overview,
    configured_markets_from_env,
    run_multi_market_paper_cycle,
)
from .operational_overview import build_operational_overview, runtime_is_consistent
from .paper_cycle import DEFAULT_MAX_CATCHUP_BARS, PaperCycleResult
from .paper_cycle_service import (
    ProductionPaperCycleSettings,
    run_production_paper_cycle,
)
from .paper_readiness_evidence import bootstrap_positive_probability
from .performance_metrics import calculate_performance_metrics
from .persistence import PaperPersistence
from .persistence_factory import build_paper_persistence
from .readiness import ReadinessCheck, ReadinessPolicy, ReadinessReport, evaluate_readiness
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


def _public_runtime_snapshot(status: HostedRuntimeStatus | None) -> dict[str, object]:
    snapshot = runtime_status_snapshot(status)
    if snapshot.get("error"):
        snapshot["error"] = "worker failure"
    return snapshot


def _display_money(value: float | None) -> str:
    return "-" if value is None else f"{value:,.2f}"


def _display_units(value: float | None) -> str:
    return "-" if value is None else f"{value:g}"


def _display_ratio(value: float | None) -> str:
    if value is None:
        return "-"
    if value == float("inf"):
        return "∞"
    return f"{value:.2f}"


def _equity_chart_svg(snapshots: tuple[BurnInSnapshot, ...]) -> str:
    if len(snapshots) < 2:
        return '<div class="chart-empty">Need at least two burn-in points.</div>'
    values = [float(snapshot.equity) for snapshot in snapshots]
    width = 900.0
    height = 240.0
    padding = 18.0
    low = min(values)
    high = max(values)
    span = high - low
    if span <= 0:
        span = max(abs(high), 1.0) * 0.01
        low -= span / 2
        high += span / 2
    usable_width = width - 2 * padding
    usable_height = height - 2 * padding
    points: list[str] = []
    for index, value in enumerate(values):
        x = padding + usable_width * index / (len(values) - 1)
        y = padding + usable_height * (high - value) / (high - low)
        points.append(f"{x:.1f},{y:.1f}")
    change = values[-1] - values[0]
    direction_class = "positive" if change >= 0 else "negative"
    return (
        '<div class="equity-chart">'
        f'<svg viewBox="0 0 {width:.0f} {height:.0f}" role="img" '
        'aria-label="Burn-in equity curve" preserveAspectRatio="none">'
        '<line class="chart-grid" x1="18" y1="18" x2="18" y2="222"></line>'
        '<line class="chart-grid" x1="18" y1="222" x2="882" y2="222"></line>'
        f'<polygon class="chart-area {direction_class}" points="18,222 {" ".join(points)} 882,222"></polygon>'
        f'<polyline class="chart-line {direction_class}" points="{" ".join(points)}"></polyline>'
        '</svg>'
        '<div class="chart-scale">'
        f'<span>{_display_money(values[0])}</span>'
        f'<span>{_display_money(values[-1])}</span>'
        '</div></div>'
    )



def _readiness_number(check: ReadinessCheck, value: float) -> str:
    if check.name in {"Max drawdown", "Total return", "Bootstrap confidence"}:
        return f"{float(value):.1%}"
    if check.name in {"Burn-in bars", "Regime coverage", "Scheduler errors"}:
        return str(int(value))
    return f"{float(value):.2f}"


def _readiness_panel(report: ReadinessReport | None) -> str:
    if report is None:
        return '<div class="readiness-empty">Readiness evidence is not complete yet.</div>'
    rows = []
    for check in report.checks:
        state = "pass" if check.passed else "fail"
        label = "PASS" if check.passed else "FAIL"
        value = _readiness_number(check, check.value)
        threshold = _readiness_number(check, check.threshold)
        rows.append(
            '<div class="readiness-row">'
            f'<span class="criterion">{html.escape(check.name)}</span>'
            f'<span class="criterion-value">{html.escape(value)}</span>'
            f'<span class="criterion-threshold">{html.escape(check.comparison)} '
            f'{html.escape(threshold)}</span>'
            f'<strong class="criterion-status {state}">{label}</strong>'
            '</div>'
        )
    return '<div class="readiness-grid">' + "".join(rows) + '</div>'


def render_dashboard(
    journal: TradeJournal,
    state_store: RuntimeStateStore | None = None,
    starting_cash: float = 100_000.0,
    *,
    runtime_status_store: HostedRuntimeStatusStore | None = None,
    persistence: PaperPersistence | None = None,
    runtime_key: str | None = None,
    markets: tuple[MarketSpec, ...] | None = None,
    market_interval: str = "5m",
) -> str:
    storage_error = False
    runtime_revision: int | None = None
    runtime_model = None
    persisted_runtime = None
    durable_runtime = persistence is not None and runtime_key is not None
    if durable_runtime:
        try:
            multi_market_view = bool(markets and len(markets) > 1)
            recent = persistence.list_trades(
                None if multi_market_view else runtime_key,
                limit=200,
            )
            persisted = persistence.load_runtime(runtime_key, starting_cash)
            persisted_runtime = persisted
            state = persisted.state
            runtime_revision = persisted.revision
            runtime_model = persisted.model
            runtime_status = persistence.load_runtime_status(runtime_key)
            load_performance = getattr(persistence, "load_trade_performance", None)
            if multi_market_view:
                trade_performance = calculate_performance_metrics(recent)
                performance_scope = "latest 200 cross-market trade events"
            elif callable(load_performance):
                trade_performance = load_performance(runtime_key)
                performance_scope = "full persisted history"
            else:
                trade_performance = calculate_performance_metrics(recent)
                performance_scope = "latest 200 trade events"
            load_burnin = getattr(persistence, "list_burnin_snapshots", None)
            burnin_snapshots = tuple(load_burnin(runtime_key)) if callable(load_burnin) else ()
            load_regimes = getattr(persistence, "list_regimes", None)
            regimes = tuple(load_regimes(runtime_key)) if callable(load_regimes) else ()
            burnin_metrics = (
                calculate_burnin_metrics(burnin_snapshots)
                if len(burnin_snapshots) >= 2
                else None
            )
        except Exception:
            recent = ()
            state = None
            runtime_status = None
            trade_performance = None
            burnin_snapshots = ()
            regimes = ()
            burnin_metrics = None
            performance_scope = "unavailable"
            storage_error = True
    else:
        recent = journal.list(limit=200)
        state = state_store.load(starting_cash) if state_store is not None else None
        runtime_status = (
            runtime_status_store.load() if runtime_status_store is not None else None
        )
        trade_performance = calculate_performance_metrics(recent)
        burnin_snapshots = ()
        regimes = ()
        burnin_metrics = None
        performance_scope = "latest 200 trade events"

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
        realized_pnl = trade_performance.realized_pnl
        trade_count = trade_performance.trade_count
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
    runtime_revision_display = (
        "-" if runtime_revision is None or storage_error else str(runtime_revision)
    )
    cycle_errors_display = (
        "-"
        if runtime_status is None or storage_error
        else str(runtime_status.consecutive_cycle_errors)
    )
    if runtime_model is None or storage_error:
        model_display = "-"
        model_checksum = "-"
    else:
        model_display = f"{runtime_model.format} v{runtime_model.version}"
        model_checksum = runtime_model.sha256[:12]

    operational_alerts: list[str] = []
    if storage_error:
        operational_alerts.append("storage unavailable")
    else:
        if engine_status == "STALE":
            operational_alerts.append("worker heartbeat expired")
        if runtime_status is not None and runtime_status.consecutive_cycle_errors > 0:
            operational_alerts.append("paper cycle reliability degraded")
        if (
            durable_runtime
            and runtime_model is None
            and state is not None
            and state.processed_bars > 0
        ):
            operational_alerts.append("model missing for initialized runtime")
        if persisted_runtime is not None and not runtime_is_consistent(persisted_runtime):
            operational_alerts.append("runtime inconsistent")
    operational_alerts_display = (
        "none" if not operational_alerts else " · ".join(operational_alerts)
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
    average_pnl_display = _display_money(
        None if trade_performance is None else trade_performance.average_pnl
    )
    profit_factor_display = _display_ratio(
        None if trade_performance is None else trade_performance.profit_factor
    )
    max_drawdown_display = _display_money(
        None if trade_performance is None else trade_performance.max_drawdown
    )
    burnin_bars = (
        burnin_snapshots[-1].processed_bars
        if burnin_snapshots
        else (state.processed_bars if state is not None and not storage_error else None)
    )
    burnin_bars_display = "-" if burnin_bars is None else str(burnin_bars)
    burnin_target = ReadinessPolicy().min_burn_in_bars
    burnin_progress = (
        0.0
        if burnin_bars is None
        else min(1.0, max(0.0, burnin_bars / burnin_target))
    )
    burnin_progress_display = f"{burnin_progress:.0%}"
    burnin_return_display = (
        "-" if burnin_metrics is None else f"{burnin_metrics.total_return:.2%}"
    )
    burnin_drawdown_display = (
        "-" if burnin_metrics is None else f"{burnin_metrics.max_drawdown:.2%}"
    )
    equity_chart = _equity_chart_svg(burnin_snapshots)
    bootstrap_probability = bootstrap_positive_probability(
        tuple(float(snapshot.equity) for snapshot in burnin_snapshots)
    )
    bootstrap_probability_display = (
        "-"
        if bootstrap_probability is None
        else f"{bootstrap_probability:.1%}"
    )
    readiness_policy = ReadinessPolicy()
    bootstrap_threshold = readiness_policy.min_positive_bootstrap_probability
    scheduler_reliable = (
        runtime_status is not None
        and not storage_error
        and runtime_status.consecutive_cycle_errors == 0
    )
    scheduler_reliability_display = (
        "-"
        if runtime_status is None or storage_error
        else ("PASS" if scheduler_reliable else "DEGRADED")
    )
    regimes_covered = len(regimes)
    regimes_covered_display = "-" if storage_error else str(regimes_covered)
    regimes_threshold = readiness_policy.min_regimes_covered
    regime_names_display = "none" if not regimes else " · ".join(regimes)
    readiness_report = None
    if (
        burnin_metrics is not None
        and bootstrap_probability is not None
        and burnin_bars is not None
        and runtime_status is not None
        and not storage_error
    ):
        readiness_report = evaluate_readiness(
            metrics=burnin_metrics,
            burn_in_bars=burnin_bars,
            bootstrap_probability_positive=bootstrap_probability,
            regimes_covered=regimes_covered,
            scheduler_errors=runtime_status.consecutive_cycle_errors,
            policy=readiness_policy,
        )
    readiness_display = (
        "-"
        if readiness_report is None
        else ("READY" if readiness_report.ready else "NOT READY")
    )
    readiness_checks_display = (
        "-"
        if readiness_report is None
        else f"{readiness_report.checks_passed} / {readiness_report.checks_total}"
    )
    sharpe_display = "-" if burnin_metrics is None else f"{burnin_metrics.sharpe:.2f}"
    sortino_display = "-" if burnin_metrics is None else f"{burnin_metrics.sortino:.2f}"
    readiness_panel = _readiness_panel(readiness_report)
    status_class = (
        "status-ok"
        if engine_status == "RUNNING" and not operational_alerts
        else ("status-warn" if not storage_error else "status-error")
    )
    market_panel = ""
    if persistence is not None and markets and len(markets) > 1:
        snapshot = build_multi_market_overview(
            persistence,
            markets,
            interval=market_interval,
            portfolio_cash=starting_cash,
        )
        portfolio = snapshot["portfolio"]
        cards = []
        for item in snapshot["markets"]:
            overview = item["overview"]
            shadow = overview.get("shadow_challenger", {})
            gate = shadow.get("promotion_gate", {})
            status = str(overview.get("engine_status", "UNKNOWN"))
            status_css = (
                "status-ok" if status == "RUNNING"
                else ("status-warn" if status in {"STARTING", "STALE"} else "status-error")
            )
            sleeve_equity = item.get("equity")
            sleeve_pnl = item.get("pnl")
            processed = overview.get("processed_bars")
            observations = shadow.get("observations", 0)
            review = "ELIGIBLE" if gate.get("eligible_for_review") else "COLLECTING"
            cards.append(
                '<div class="market-card">'
                f'<div class="market-card-head"><strong>{html.escape(str(item["label"]))}</strong>'
                f'<span class="status-badge {status_css}">{html.escape(status)}</span></div>'
                f'<small>{html.escape(str(item["symbol"]))} · allocation {float(item["allocation"]):.0%}</small>'
                '<div class="market-grid">'
                f'<div><small>Equity</small><strong>{_display_money(sleeve_equity)}</strong></div>'
                f'<div><small>PnL</small><strong>{_display_money(sleeve_pnl)}</strong></div>'
                f'<div><small>Bars</small><strong>{"-" if processed is None else processed}</strong></div>'
                f'<div><small>Shadow</small><strong>{observations}</strong></div>'
                f'<div><small>Promotion gate</small><strong>{review}</strong></div>'
                '</div></div>'
            )
        market_panel = (
            '<section class="section" id="markets">'
            '<div class="section-head"><h2>Multi-market portfolio</h2>'
            '<small>normalized sleeves · independent runtimes</small></div>'
            '<div class="metrics">'
            f'<div class="metric primary"><small>Portfolio equity</small><strong>{_display_money(float(portfolio["equity"]))}</strong></div>'
            f'<div class="metric"><small>Portfolio PnL</small><strong>{_display_money(float(portfolio["pnl"]))}</strong></div>'
            f'<div class="metric"><small>Healthy markets</small><strong>{portfolio["healthy_markets"]} / {portfolio["markets"]}</strong></div>'
            '</div><div class="market-cards">'
            + "".join(cards)
            + '</div></section>'
        )

    return f"""<!doctype html>
<html><head><meta charset="utf-8"><meta http-equiv="refresh" content="2">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>AI Trading — Live</title>
<style>
:root{{color-scheme:dark;--bg:#050914;--surface:rgba(13,22,39,.86);--surface-2:rgba(8,16,31,.86);--border:rgba(148,163,184,.14);--text:#f5f8ff;--muted:#8998af;--blue:#71a7ff;--cyan:#56d9e8;--green:#63e6a3;--amber:#ffd27a;--red:#ff8a8a}}
*{{box-sizing:border-box}}
html{{scroll-behavior:smooth}}
body{{font-family:Inter,ui-sans-serif,system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;margin:0;background:radial-gradient(circle at 15% -10%,rgba(70,113,255,.18),transparent 32%),radial-gradient(circle at 85% 0%,rgba(55,211,211,.10),transparent 27%),var(--bg);color:var(--text);min-height:100vh}}
body:before{{content:"";position:fixed;inset:0;pointer-events:none;background-image:linear-gradient(rgba(255,255,255,.018) 1px,transparent 1px),linear-gradient(90deg,rgba(255,255,255,.018) 1px,transparent 1px);background-size:42px 42px;mask-image:linear-gradient(to bottom,black,transparent 78%)}}
main{{max-width:1540px;margin:auto;padding:18px 20px 40px;position:relative}}
h1,h2,h3{{margin:0}}
h1{{font-size:clamp(1.65rem,4vw,2.45rem);letter-spacing:-.035em}}
h2{{font-size:1.02rem;letter-spacing:-.01em}}
small,.muted{{color:var(--muted)}}
.premium-shell{{position:relative}}
.top-nav{{position:sticky;top:10px;z-index:20;display:flex;align-items:center;justify-content:space-between;gap:14px;margin-bottom:14px;padding:10px 12px;background:rgba(7,13,25,.78);border:1px solid var(--border);border-radius:16px;backdrop-filter:blur(18px);box-shadow:0 12px 36px rgba(0,0,0,.28)}}
.brand{{display:flex;align-items:center;gap:10px;font-weight:800;letter-spacing:-.02em}}
.brand-mark{{width:30px;height:30px;border-radius:9px;display:grid;place-items:center;background:linear-gradient(135deg,#6ea8ff,#58e0cf);color:#04101d;box-shadow:0 0 26px rgba(91,189,255,.28)}}
.nav-links{{display:flex;gap:6px;overflow:auto;scrollbar-width:none}}
.nav-links::-webkit-scrollbar{{display:none}}
.nav-links a{{color:#afbdd0;text-decoration:none;font-size:.8rem;font-weight:650;padding:7px 9px;border-radius:9px;white-space:nowrap}}
.nav-links a:hover{{background:rgba(255,255,255,.06);color:#fff}}
.card{{background:linear-gradient(180deg,rgba(18,29,49,.86),rgba(10,18,33,.88));border:1px solid var(--border);border-radius:22px;padding:20px;box-shadow:0 28px 80px rgba(0,0,0,.34),inset 0 1px 0 rgba(255,255,255,.035);backdrop-filter:blur(16px)}}
.header{{display:flex;justify-content:space-between;gap:18px;align-items:flex-start;flex-wrap:wrap;padding-bottom:16px}}
.header-copy{{max-width:760px}}
.eyebrow{{display:flex;align-items:center;gap:7px;color:#9cafca;text-transform:uppercase;letter-spacing:.13em;font-size:.69rem;font-weight:800;margin-bottom:7px}}
.live-dot{{width:7px;height:7px;border-radius:50%;background:var(--green);box-shadow:0 0 0 5px rgba(99,230,163,.08),0 0 18px rgba(99,230,163,.7)}}
.header-subtitle{{display:block;margin-top:7px;font-size:.86rem}}
.header-meta{{display:flex;gap:8px;align-items:center;flex-wrap:wrap;justify-content:flex-end}}
.pill{{display:inline-flex;align-items:center;gap:7px;padding:7px 10px;border-radius:999px;background:rgba(255,255,255,.045);border:1px solid var(--border);font-size:.78rem;color:#c7d2e3}}
.status-badge{{display:inline-flex;align-items:center;gap:8px;border-radius:999px;padding:7px 11px;font-size:.78rem;font-weight:800;border:1px solid}}
.status-ok{{color:#bdf7d6;background:rgba(20,94,60,.28);border-color:rgba(99,230,163,.24)}}
.status-warn{{color:#ffe2a3;background:rgba(130,91,12,.22);border-color:rgba(255,210,122,.24)}}
.status-error{{color:#ffc0c0;background:rgba(115,29,29,.26);border-color:rgba(255,138,138,.25)}}
.hero-kpis{{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:10px;margin:2px 0 18px}}
.hero-kpi{{position:relative;overflow:hidden;padding:15px 16px;border-radius:15px;background:linear-gradient(145deg,rgba(22,35,58,.9),rgba(9,18,34,.92));border:1px solid var(--border)}}
.hero-kpi:after{{content:"";position:absolute;width:120px;height:120px;right:-55px;top:-65px;border-radius:50%;background:rgba(101,160,255,.08)}}
.hero-kpi small{{display:block;font-size:.72rem;text-transform:uppercase;letter-spacing:.08em;font-weight:750}}
.hero-kpi strong{{display:block;margin-top:6px;font-size:clamp(1.28rem,3vw,1.72rem);letter-spacing:-.03em;overflow-wrap:anywhere}}
.section{{scroll-margin-top:76px;margin-top:12px;padding:16px;border:1px solid var(--border);border-radius:17px;background:rgba(7,14,28,.58)}}
.section-head{{display:flex;justify-content:space-between;align-items:end;gap:12px;margin-bottom:11px}}
.section-head h2{{display:flex;align-items:center;gap:8px}}
.section-head h2:before{{content:"";display:inline-block;width:5px;height:18px;border-radius:999px;background:linear-gradient(var(--blue),var(--cyan));box-shadow:0 0 16px rgba(96,176,255,.28)}}
.metrics{{display:grid;grid-template-columns:repeat(auto-fit,minmax(155px,1fr));gap:9px}}
.metric{{background:linear-gradient(145deg,rgba(12,23,42,.78),rgba(7,15,29,.82));border:1px solid rgba(148,163,184,.11);border-radius:13px;padding:13px;min-width:0;transition:transform .18s ease,border-color .18s ease}}
.metric:hover{{transform:translateY(-1px);border-color:rgba(113,167,255,.24)}}
.metric small{{display:block;font-size:.72rem}}
.metric strong{{display:block;font-size:1.15rem;margin-top:5px;letter-spacing:-.025em;overflow-wrap:anywhere}}
.metric.primary{{background:linear-gradient(145deg,rgba(27,52,86,.62),rgba(9,22,42,.85));border-color:rgba(113,167,255,.19)}}
.metric.primary strong{{font-size:1.42rem}}
.alert-box{{margin-top:12px;padding:11px 13px;border-radius:11px;background:rgba(11,22,39,.72);border:1px solid var(--border);font-size:.84rem}}
.alert-box.warn{{border-color:rgba(255,210,122,.28);background:rgba(87,62,9,.19);color:#ffe0a0}}
.runtime-reason{{display:block;margin-top:7px;line-height:1.45;font-size:.77rem}}
.readiness-grid{{display:grid;gap:7px;margin-top:12px}}
.readiness-row{{display:grid;grid-template-columns:minmax(145px,1.5fr) minmax(72px,.65fr) minmax(86px,.75fr) 68px;align-items:center;gap:9px;padding:10px 12px;border:1px solid rgba(148,163,184,.11);border-radius:11px;background:rgba(7,15,29,.68)}}
.criterion{{font-size:.82rem;font-weight:700;color:#d9e3f2}}
.criterion-value,.criterion-threshold{{font-size:.8rem;color:#9fb0c8;text-align:right}}
.criterion-status{{font-size:.72rem;text-align:center;padding:5px 7px;border-radius:999px;border:1px solid}}
.criterion-status.pass{{color:#bdf7d6;background:rgba(20,94,60,.28);border-color:rgba(99,230,163,.24)}}
.criterion-status.fail{{color:#ffc0c0;background:rgba(115,29,29,.26);border-color:rgba(255,138,138,.25)}}
.readiness-empty{{margin-top:12px;padding:14px;border:1px dashed #31425f;border-radius:11px;color:var(--muted);text-align:center;font-size:.8rem}}
.equity-chart{{margin-top:11px;background:linear-gradient(180deg,rgba(5,11,22,.88),rgba(8,16,30,.74));border:1px solid var(--border);border-radius:15px;padding:11px;overflow:hidden}}
.equity-chart svg{{display:block;width:100%;height:240px;filter:drop-shadow(0 12px 24px rgba(0,0,0,.22))}}
.chart-line{{fill:none;stroke-width:3.2;stroke-linecap:round;stroke-linejoin:round}}
.chart-line.positive{{stroke:var(--green)}}
.chart-line.negative{{stroke:var(--red)}}
.chart-area{{opacity:.12}}
.chart-area.positive{{fill:var(--green)}}
.chart-area.negative{{fill:var(--red)}}
.chart-grid{{stroke:#293853;stroke-width:1}}
.chart-scale{{display:flex;justify-content:space-between;font-size:.74rem;color:var(--muted);margin-top:4px}}
.chart-empty{{margin-top:11px;padding:18px;border:1px dashed #31425f;border-radius:13px;color:var(--muted);text-align:center}}
.progress-track{{height:8px;background:#07101e;border:1px solid #24334d;border-radius:999px;overflow:hidden;margin-top:9px}}
.progress-fill{{height:100%;background:linear-gradient(90deg,#6d9eff,#60e1cd);border-radius:999px;box-shadow:0 0 16px rgba(96,225,205,.24)}}
.table-scroll{{overflow-x:auto;-webkit-overflow-scrolling:touch;margin-top:10px;border:1px solid var(--border);border-radius:13px;background:rgba(6,13,25,.68)}}
table{{width:100%;border-collapse:collapse;min-width:900px}}
th,td{{padding:11px 12px;border-bottom:1px solid rgba(148,163,184,.10);text-align:right;white-space:nowrap}}
th{{position:sticky;top:0;background:#0d1829;color:#aebdd0;font-size:.7rem;text-transform:uppercase;letter-spacing:.06em}}
td{{font-size:.83rem}}
th:first-child,td:first-child,th:nth-child(2),td:nth-child(2),th:nth-child(3),td:nth-child(3),th:last-child,td:last-child{{text-align:left}}
tbody tr:hover{{background:rgba(113,167,255,.045)}}
.market-cards{{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px;margin-top:12px}}
.market-card{{padding:14px;border:1px solid var(--border);border-radius:14px;background:rgba(7,15,28,.72)}}
.market-card-head{{display:flex;align-items:center;justify-content:space-between;gap:10px;margin-bottom:4px}}
.market-card-head strong{{font-size:1rem}}
.market-grid{{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:9px;margin-top:12px}}
.market-grid div{{padding:9px;border-radius:10px;background:rgba(12,24,42,.72)}}
.market-grid small{{display:block;color:var(--muted);font-size:.68rem;margin-bottom:3px}}
.market-grid strong{{font-size:.9rem}}
.footer-note{{text-align:center;color:#687891;font-size:.72rem;padding:16px 4px 0}}
@media (max-width:900px){{
  .hero-kpis{{grid-template-columns:repeat(2,minmax(0,1fr))}}
  .market-cards{{grid-template-columns:1fr}}
  .nav-links{{max-width:58vw}}
}}
@media (max-width:700px){{
  main{{padding:10px 9px 24px}}
  .top-nav{{top:6px;border-radius:13px;padding:8px 9px}}
  .brand span:last-child{{display:none}}
  .nav-links{{max-width:72vw}}
  .card{{padding:13px;border-radius:17px}}
  .header{{padding-bottom:13px}}
  .metrics{{grid-template-columns:repeat(2,minmax(0,1fr))}}
  .metric{{padding:11px}}
  .metric strong{{font-size:1.02rem}}
  .metric.primary strong{{font-size:1.18rem}}
  .section{{padding:12px;border-radius:14px}}
  .readiness-row{{grid-template-columns:1fr auto;gap:6px 10px}}
  .criterion-value,.criterion-threshold{{text-align:left}}
  .criterion-status{{grid-column:2;grid-row:1 / span 2}}
  .criterion-threshold{{grid-column:1}}
  .equity-chart svg{{height:180px}}
}}
@media (max-width:430px){{
  .hero-kpis{{grid-template-columns:1fr 1fr}}
  .hero-kpi{{padding:12px}}
  .hero-kpi strong{{font-size:1.15rem}}
  .metrics{{grid-template-columns:1fr 1fr}}
  .section-head{{align-items:flex-start;flex-direction:column;gap:4px}}
}}
</style></head><body><main>
<div class="premium-shell">
<nav class="top-nav" aria-label="Dashboard sections">
<div class="brand"><span class="brand-mark">AI</span><span>Trading Terminal</span></div>
<div class="nav-links">
<a href="#overview">Overview</a>
<a href="#markets">Markets</a>
<a href="#performance">Performance</a>
<a href="#burnin">Burn-in</a>
<a href="#evidence">Evidence</a>
<a href="#trades">Trades</a>
</div>
</nav>

<div class="card">
<div class="header">
<div class="header-copy">
<div class="eyebrow"><span class="live-dot"></span> Paper trading · live telemetry</div>
<h1>AI Trading Terminal</h1>
<small class="header-subtitle">Premium read-only control center · auto refresh 2s · durable hosted runtime</small>
</div>
<div class="header-meta">
<span class="pill">{html.escape(market)}</span>
<span class="status-badge {status_class}">{html.escape(engine_status)}</span>
</div>
</div>

<div class="hero-kpis">
<div class="hero-kpi"><small>Equity</small><strong>{_display_money(equity)}</strong></div>
<div class="hero-kpi"><small>Realized PnL</small><strong>{pnl_display}</strong></div>
<div class="hero-kpi"><small>Signal</small><strong>{html.escape(signal)}</strong></div>
<div class="hero-kpi"><small>Burn-in</small><strong>{burnin_progress_display}</strong></div>
</div>

<section class="section" id="overview">
<div class="section-head"><h2>System health</h2><small>runtime observability</small></div>
<div class="metrics">
<div class="metric primary"><small>Engine</small><strong>{html.escape(engine_status)}</strong></div>
<div class="metric"><small>Heartbeat age</small><strong>{html.escape(heartbeat_age)}</strong></div>
<div class="metric"><small>Consecutive cycle errors</small><strong>{cycle_errors_display}</strong></div>
<div class="metric"><small>Processed bars</small><strong>{processed_bars_display}</strong></div>
<div class="metric"><small>Runtime revision</small><strong>{runtime_revision_display}</strong></div>
<div class="metric"><small>Model</small><strong>{html.escape(model_display)}</strong></div>
<div class="metric"><small>Model checksum</small><strong>{html.escape(model_checksum)}</strong></div>
</div>
<div class="alert-box {'warn' if operational_alerts else ''}">
<strong>Operational alerts: {html.escape(operational_alerts_display)}</strong>
</div>
<small class="runtime-reason">Last heartbeat: {html.escape(last_heartbeat)} · Last cycle: {html.escape(last_cycle)}</small>
<small class="runtime-reason">Last processed: {html.escape(last_processed)} · Model checksum: {html.escape(model_checksum)}</small>
</section>

<section class="section">
<div class="section-head"><h2>Trading state</h2><small>paper execution state</small></div>
<div class="metrics">
<div class="metric primary"><small>Signal</small><strong>{html.escape(signal)}</strong></div>
<div class="metric primary"><small>Risk decision</small><strong>{html.escape(risk_decision)}</strong></div>
<div class="metric"><small>AI confidence</small><strong>{html.escape(confidence)}</strong></div>
<div class="metric"><small>Equity</small><strong>{_display_money(equity)}</strong></div>
<div class="metric"><small>Cash</small><strong>{_display_money(cash)}</strong></div>
<div class="metric"><small>Open units</small><strong>{_display_units(units)}</strong></div>
<div class="metric"><small>Position value</small><strong>{_display_money(position_value)}</strong></div>
</div>
<small class="runtime-reason">Last engine reason: {html.escape(decision_reason)}</small>
</section>

{market_panel}
<section class="section" id="performance">
<div class="section-head"><h2>Performance</h2><small>Performance window: {html.escape(performance_scope)}</small></div>
<div class="metrics">
<div class="metric primary"><small>Realized PnL</small><strong>{pnl_display}</strong></div>
<div class="metric"><small>Trades</small><strong>{trade_count_display}</strong></div>
<div class="metric"><small>Avg PnL / trade</small><strong>{average_pnl_display}</strong></div>
<div class="metric"><small>Profit factor</small><strong>{profit_factor_display}</strong></div>
<div class="metric"><small>Max realized DD</small><strong>{max_drawdown_display}</strong></div>
<div class="metric"><small>Recent win rate</small><strong>{win_rate_display}</strong></div>
<div class="metric"><small>Wins / losses</small><strong>{wins_losses_display}</strong></div>
<div class="metric"><small>Active symbols</small><strong>{active_symbols_display}</strong></div>
</div>
</section>

<section class="section" id="burnin">
<div class="section-head"><h2>Burn-in evidence</h2><small>durable equity history</small></div>
<div class="metrics">
<div class="metric primary"><small>Burn-in bars</small><strong>{burnin_bars_display} / {burnin_target}</strong></div>
<div class="metric"><small>Burn-in progress</small><strong>{burnin_progress_display}</strong>
<div class="progress-track"><div class="progress-fill" style="width:{burnin_progress_display}"></div></div></div>
<div class="metric"><small>Equity return</small><strong>{burnin_return_display}</strong></div>
<div class="metric"><small>Equity max DD</small><strong>{burnin_drawdown_display}</strong></div>
</div>
{equity_chart}
</section>

<section class="section" id="evidence">
<div class="section-head"><h2>Quant evidence</h2><small>readiness inputs without false precision</small></div>
<div class="metrics">
<div class="metric primary"><small>Bootstrap positive probability</small><strong>{bootstrap_probability_display}</strong></div>
<div class="metric"><small>Bootstrap threshold</small><strong>{bootstrap_threshold:.0%}</strong></div>
<div class="metric"><small>Scheduler reliability</small><strong>{scheduler_reliability_display}</strong></div>
<div class="metric"><small>Regime coverage</small><strong>{regimes_covered_display} / {regimes_threshold}</strong></div>
<div class="metric"><small>Sharpe</small><strong>{sharpe_display}</strong></div>
<div class="metric"><small>Sortino</small><strong>{sortino_display}</strong></div>
<div class="metric primary"><small>Full readiness</small><strong>{readiness_display}</strong></div>
<div class="metric"><small>Readiness checks</small><strong>{readiness_checks_display}</strong></div>
</div>
{readiness_panel}
<small class="runtime-reason">Observed regimes: {html.escape(regime_names_display)}.</small>
<small class="runtime-reason">Each readiness criterion shows its current value, required threshold and PASS/FAIL result. Sharpe and Sortino are annualized from the actual elapsed time covered by durable burn-in timestamps.</small>
</section>

<section class="section" id="trades">
<div class="section-head"><h2>Recent trades</h2><small>latest 200 events</small></div>
<div class="table-scroll">
<table><thead><tr><th>UTC</th><th>Symbol</th><th>Side</th><th>Qty</th><th>Price</th>
<th>Status</th><th>PnL</th><th>Confidence</th><th>Strategy</th></tr></thead>
<tbody>{rows}</tbody></table>
</div>
</section>
<div class="footer-note">AI Trading · paper runtime · read-only observability</div>
</div>
</div></main></body></html>"""


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
    effective_markets = configured_markets_from_env()
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
            max_catchup_bars=DEFAULT_MAX_CATCHUP_BARS,
            poll_seconds=300.0,
            shadow_challenger_enabled=effective_settings.shadow_challenger,
        )

        def execute_paper_cycle() -> PaperCycleResult:
            if len(effective_markets) > 1:
                return run_multi_market_paper_cycle(
                    effective_markets,
                    period=cycle_settings.period,
                    interval=cycle_settings.interval,
                    max_catchup_bars=cycle_settings.max_catchup_bars,
                    poll_seconds=cycle_settings.poll_seconds,
                    shadow_challenger_enabled=cycle_settings.shadow_challenger_enabled,
                    persistence=backend,
                )
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
            if path == "/api/overview":
                self._send_json(
                    build_operational_overview(
                        backend,
                        runtime_key,
                        starting_cash,
                    )
                )
                return
            if path == "/api/markets":
                self._send_json(
                    build_multi_market_overview(
                        backend,
                        effective_markets,
                        interval=effective_settings.interval,
                        portfolio_cash=starting_cash,
                    )
                )
                return
            if path == "/api/status":
                self._send_json(load_status_snapshot())
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
                markets=effective_markets,
                market_interval=effective_settings.interval,
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

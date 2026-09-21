from __future__ import annotations

import html
import json
import os
from collections.abc import Callable
from datetime import UTC, datetime
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
from .persistence import PaperPersistence, SchedulerDelivery, build_runtime_key
from .persistence_factory import build_paper_persistence
from .readiness import ReadinessCheck, ReadinessPolicy, ReadinessReport, evaluate_readiness
from .runtime_state import RuntimeStateStore
from .runtime_status import HostedRuntimeStatus, HostedRuntimeStatusStore, runtime_status_snapshot
from .scheduler_endpoint import (
    handle_scheduler_request,
    scheduler_delivery_overview,
    scheduler_telemetry_payload,
)
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


def _trade_pnl_known(trade: object) -> bool:
    marker = getattr(trade, "pnl_known", None)
    if marker is None:
        return float(getattr(trade, "pnl", 0.0)) != 0.0
    return bool(marker)


def _display_trade_pnl(trade: object) -> str:
    if not _trade_pnl_known(trade):
        return "—"
    return f"{float(getattr(trade, 'pnl', 0.0)):.2f}"


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
            load_portfolio_performance = getattr(
                persistence,
                "load_portfolio_trade_performance",
                None,
            )
            if multi_market_view and callable(load_portfolio_performance):
                multi_runtime_keys = tuple(
                    build_runtime_key(market.symbol, market_interval)
                    for market in markets or ()
                )
                trade_performance = load_portfolio_performance(
                    multi_runtime_keys
                )
                performance_scope = "full persisted cross-market history"
                performance_is_recent = False
            elif multi_market_view:
                trade_performance = calculate_performance_metrics(recent)
                performance_scope = "latest 200 cross-market trade events"
                performance_is_recent = True
            elif callable(load_performance):
                trade_performance = load_performance(runtime_key)
                performance_scope = "full persisted history"
                performance_is_recent = False
            else:
                trade_performance = calculate_performance_metrics(recent)
                performance_scope = "latest 200 trade events"
                performance_is_recent = True
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
        performance_is_recent = True
        burnin_snapshots = ()
        regimes = ()
        burnin_metrics = None
        performance_scope = "latest 200 trade events"

    trades = reversed(recent)
    if storage_error:
        realized_pnl: float | None = None
        trade_count: int | None = None
        pnl_observations: int | None = None
        pnl_coverage_total: int | None = None
        pnl_coverage_recent = False
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
        persisted_observations = getattr(
            trade_performance,
            "pnl_observations",
            None,
        )
        if persisted_observations is None:
            pnl_observations = sum(1 for trade in recent if _trade_pnl_known(trade))
        else:
            pnl_observations = int(persisted_observations)
        pnl_coverage_total = len(recent) if performance_is_recent else trade_count
        pnl_coverage_recent = performance_is_recent
        if pnl_observations == 0:
            realized_pnl = None
        wins = sum(
            1
            for trade in recent
            if _trade_pnl_known(trade) and trade.pnl > 0
        )
        losses = sum(
            1
            for trade in recent
            if _trade_pnl_known(trade) and trade.pnl < 0
        )
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
            f"<td>{_display_trade_pnl(t)}</td>"
            f"<td>{'-' if t.confidence is None else f'{t.confidence:.1%}'}</td>"
            f"<td>{html.escape(t.strategy)}</td>"
            "</tr>"
            for t in trades
        )
        if not rows:
            rows = '<tr><td colspan="9">No trades recorded yet.</td></tr>'

    trade_count_display = "-" if trade_count is None else str(trade_count)
    pnl_display = _display_money(realized_pnl)
    if pnl_observations is None or pnl_coverage_total is None:
        pnl_coverage_display = "-"
    else:
        recent_suffix = " recent" if pnl_coverage_recent else ""
        pnl_coverage_display = (
            f"{pnl_observations} / {pnl_coverage_total}{recent_suffix}"
        )
    win_rate_display = "-" if win_rate is None else f"{win_rate:.1%}"
    wins_losses_display = "-" if wins is None or losses is None else f"{wins} / {losses}"
    active_symbols_display = "-" if active_symbols is None else str(active_symbols)
    average_pnl_display = _display_money(
        None
        if trade_performance is None or pnl_observations == 0
        else trade_performance.average_pnl
    )
    profit_factor_display = _display_ratio(
        None if trade_performance is None else trade_performance.profit_factor
    )
    max_drawdown_display = _display_money(
        None
        if trade_performance is None or pnl_observations == 0
        else trade_performance.max_drawdown
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

    scheduler_panel = ""
    if persistence is not None:
        try:
            list_deliveries = getattr(persistence, "list_scheduler_deliveries", None)
            deliveries = tuple(list_deliveries(limit=20)) if callable(list_deliveries) else ()
            scheduler_overview = scheduler_delivery_overview(deliveries)
            scheduler_verified = bool(scheduler_overview["cloudflare_delivery_verified"])
            scheduler_delivery_count = int(scheduler_overview["delivery_count"])
            scheduler_successes = int(
                scheduler_overview["consecutive_cloudflare_successes"]
            )
            scheduler_last_source = str(scheduler_overview["last_source"] or "-")
            scheduler_last_status = (
                "-"
                if scheduler_overview["last_status_code"] is None
                else str(scheduler_overview["last_status_code"])
            )
            scheduler_last_delivery = str(
                scheduler_overview["last_delivery_timestamp_utc"] or "-"
            )
            scheduler_state = (
                "VERIFIED"
                if scheduler_verified
                else ("COLLECTING" if scheduler_delivery_count else "WAITING")
            )
            scheduler_state_class = "status-ok" if scheduler_verified else "status-warn"
            scheduler_panel = f"""
<section class="section" id="scheduler">
<div class="section-head"><h2>Scheduler delivery</h2><small>durable external-trigger evidence</small></div>
<div class="metrics">
<div class="metric primary"><small>Cloudflare delivery</small><strong class="{scheduler_state_class}">{scheduler_state}</strong></div>
<div class="metric"><small>Consecutive Cloudflare successes</small><strong>{scheduler_successes} / 3</strong></div>
<div class="metric"><small>Recent deliveries</small><strong>{scheduler_delivery_count}</strong></div>
<div class="metric"><small>Last source</small><strong>{html.escape(scheduler_last_source)}</strong></div>
<div class="metric"><small>Last HTTP status</small><strong>{html.escape(scheduler_last_status)}</strong></div>
<div class="metric"><small>Last delivery</small><strong>{html.escape(scheduler_last_delivery)}</strong></div>
</div>
<small class="runtime-reason">Verification requires at least three consecutive successful Cloudflare deliveries. Authentication material is never persisted or displayed.</small>
</section>
"""
        except Exception:
            scheduler_panel = """
<section class="section" id="scheduler">
<div class="section-head"><h2>Scheduler delivery</h2><small>durable external-trigger evidence</small></div>
<div class="alert-box warn"><strong>Scheduler telemetry unavailable.</strong></div>
</section>
"""

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
            mtf_shadow = overview.get("mtf_shadow_challenger", {})
            mtf_gate = mtf_shadow.get("promotion_gate", {})
            status = str(overview.get("engine_status", "UNKNOWN"))
            status_css = (
                "status-ok" if status == "RUNNING"
                else ("status-warn" if status in {"STARTING", "STALE"} else "status-error")
            )
            sleeve_equity = item.get("equity")
            sleeve_pnl = item.get("pnl")
            processed = overview.get("processed_bars")
            cycle_duration = item.get("cycle_duration_seconds")
            cycle_duration_display = (
                "-" if cycle_duration is None else f"{float(cycle_duration):.1f}s"
            )
            heartbeat_age_seconds = item.get("heartbeat_age_seconds")
            heartbeat_age_display = (
                "-" if heartbeat_age_seconds is None
                else (
                    f"{float(heartbeat_age_seconds):.0f}s"
                    if float(heartbeat_age_seconds) < 120
                    else f"{float(heartbeat_age_seconds) / 60.0:.1f}m"
                )
            )
            freshness = str(item.get("freshness") or "OFF")
            session_open = item.get("session_open")
            session_display = (
                "OPEN" if session_open is True
                else "CLOSED" if session_open is False
                else "UNKNOWN"
            )
            mtf_candidate = mtf_shadow.get("candidate_config")
            mtf_horizon = mtf_shadow.get("horizon_minutes")
            mtf_candidate_name = (
                html.escape(str(mtf_candidate.get("config_name")))
                if isinstance(mtf_candidate, dict)
                else "UNVALIDATED"
            )
            mtf_label = (
                f"MTF {int(mtf_horizon)}m"
                if mtf_horizon is not None
                else "MTF candidate"
            )
            mtf_cycle_display = (
                "DISABLED"
                if mtf_candidate is None
                else ("YES" if item.get("mtf_evaluated") else "NO")
            )
            observations = shadow.get("observations", 0)
            mtf_observations = mtf_shadow.get("observations", 0)
            mtf_directional = mtf_shadow.get("directional_observations", 0)
            mtf_directional_rate = float(mtf_shadow.get("directional_rate", 0.0) or 0.0)
            mtf_distribution = mtf_shadow.get("label_distribution", {})
            review = "ELIGIBLE" if gate.get("eligible_for_review") else "COLLECTING"
            mtf_review = (
                "MTF UNVALIDATED"
                if mtf_candidate is None
                else (
                    "ELIGIBLE"
                    if mtf_gate.get("eligible_for_review")
                    else "MTF COLLECTING"
                )
            )
            mtf_score_delta = mtf_shadow.get("score_delta")
            mtf_score_display = (
                "-" if mtf_score_delta is None else f"{float(mtf_score_delta):+.3f}"
            )
            signal = item.get("signal") or "-"
            signal_css = {
                "LONG": "signal-long",
                "SHORT": "signal-short",
                "FLAT": "signal-flat",
            }.get(str(signal), "signal-neutral")
            market_confidence = item.get("confidence")
            confidence_value = (
                0.0 if market_confidence is None
                else min(1.0, max(0.0, float(market_confidence)))
            )
            confidence_display = (
                "-" if market_confidence is None else f"{confidence_value:.1%}"
            )
            shadow_progress = min(100.0, float(observations) / 250.0 * 100.0)
            mtf_shadow_progress = min(
                100.0,
                float(mtf_observations) / 500.0 * 100.0,
            )
            mtf_directional_progress = min(
                100.0,
                float(mtf_directional) / 100.0 * 100.0,
            )
            market_tone = {
                "GC=F": "gold",
                "^GDAXI": "dax",
                "BTC-USD": "btc",
            }.get(str(item["symbol"]), "default")
            market_mark = {
                "GC=F": "AU",
                "^GDAXI": "DX",
                "BTC-USD": "₿",
            }.get(str(item["symbol"]), "AI")
            pnl_css = (
                "value-positive" if sleeve_pnl is not None and float(sleeve_pnl) > 0
                else "value-negative" if sleeve_pnl is not None and float(sleeve_pnl) < 0
                else "value-neutral"
            )
            reason = html.escape(str(item.get("reason") or "waiting for next eligible bar"))
            cards.append(
                f'<article class="market-card {market_tone}">'
                '<div class="market-card-glow"></div>'
                '<div class="market-card-head">'
                f'<div class="market-identity"><span class="market-mark">{market_mark}</span>'
                f'<div><strong>{html.escape(str(item["label"]))}</strong>'
                f'<small>{html.escape(str(item["symbol"]))} · {float(item["allocation"]):.0%} sleeve</small></div></div>'
                f'<span class="status-badge {status_css}">{html.escape(status)}</span></div>'
                f'<div class="market-signal-row"><span class="signal-chip {signal_css}">{html.escape(str(signal))}</span>'
                f'<span class="market-confidence-label">Confidence <strong>{confidence_display}</strong></span></div>'
                '<div class="confidence-meter"><span '
                f'style="width:{confidence_value * 100:.1f}%"></span></div>'
                '<div class="market-grid">'
                f'<div><small>Equity</small><strong>{_display_money(sleeve_equity)}</strong></div>'
                f'<div><small>PnL</small><strong class="{pnl_css}">{_display_money(sleeve_pnl)}</strong></div>'
                f'<div><small>Processed bars</small><strong>{"-" if processed is None else processed}</strong></div>'
                f'<div><small>Cycle latency</small><strong>{cycle_duration_display}</strong></div>'
                f'<div><small>Freshness</small><strong>{html.escape(freshness)}</strong></div>'
                f'<div><small>Session</small><strong>{session_display}</strong></div>'
                f'<div><small>Heartbeat age</small><strong>{heartbeat_age_display}</strong></div>'
                f'<div><small>MTF this cycle</small><strong>{mtf_cycle_display}</strong></div>'
                f'<div><small>Shadow 5m</small><strong>{observations}</strong></div>'
                f'<div><small>{mtf_label}</small><strong>{mtf_observations}</strong></div>'
                f'<div><small>MTF candidate</small><strong>{mtf_candidate_name}</strong></div>'
                f'<div><small>Directional MTF</small><strong>{mtf_directional} · {mtf_directional_rate:.0%}</strong></div>'
                f'<div><small>MTF labels</small><strong>L {mtf_distribution.get("long", 0)} · F {mtf_distribution.get("flat", 0)} · S {mtf_distribution.get("short", 0)}</strong></div>'
                f'<div><small>MTF score Δ</small><strong>{mtf_score_display}</strong></div>'
                '</div>'
                '<div class="shadow-row">'
                f'<div><span>5m challenger evidence</span><strong>{observations} / 250</strong></div>'
                f'<div class="shadow-track"><span style="width:{shadow_progress:.1f}%"></span></div>'
                '</div>'
                '<div class="shadow-row">'
                f'<div><span>{mtf_label} · 5m/15m/1h/4h</span><strong>{mtf_observations} / 500</strong></div>'
                f'<div class="shadow-track mtf-track"><span style="width:{mtf_shadow_progress:.1f}%"></span></div>'
                '</div>'
                '<div class="shadow-row">'
                f'<div><span>Directional MTF evidence</span><strong>{mtf_directional} / 100</strong></div>'
                f'<div class="shadow-track mtf-track"><span style="width:{mtf_directional_progress:.1f}%"></span></div>'
                '</div>'
                f'<div class="market-card-footer"><span class="gate-chip">{review}</span>'
                f'<span class="gate-chip">{mtf_review}</span><small>{reason}</small></div>'
                '</article>'
            )
        portfolio_pnl = float(portfolio["pnl"])
        portfolio_pnl_css = (
            "value-positive" if portfolio_pnl > 0
            else "value-negative" if portfolio_pnl < 0
            else "value-neutral"
        )
        market_panel = (
            '<section class="section markets-section" id="markets">'
            '<div class="section-head"><div><div class="section-kicker">LIVE MARKET MATRIX</div>'
            '<h2>Multi-market portfolio</h2></div>'
            '<small>normalized sleeves · isolated runtimes · 5m cadence</small></div>'
            '<div class="portfolio-ribbon">'
            f'<div><small>Portfolio equity</small><strong>{_display_money(float(portfolio["equity"]))}</strong></div>'
            f'<div><small>Portfolio PnL</small><strong class="{portfolio_pnl_css}">{_display_money(portfolio_pnl)}</strong></div>'
            f'<div><small>Storage healthy</small><strong>{portfolio["healthy_markets"]} / {portfolio["markets"]}</strong></div>'
            f'<div><small>Engines running</small><strong>{portfolio["running_markets"]} / {portfolio["markets"]}</strong></div>'
            f'<div><small>Markets with alerts</small><strong>{portfolio["alert_markets"]}</strong></div>'
            f'<div><small>Sessions closed</small><strong>{portfolio["closed_markets"]}</strong></div>'
            f'<div><small>Catch-up / provider gaps</small><strong>{portfolio["catching_up_markets"]} / {portfolio["provider_gap_markets"]}</strong></div>'
            '<div><small>Execution mode</small><strong>PAPER ONLY</strong></div>'
            '</div><div class="market-cards">'
            + "".join(cards)
            + '</div></section>'
        )

    return f"""<!doctype html>
<html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>AI Trading — Live</title>
<style>
html.dashboard-refreshing, html.dashboard-refreshing body {{ overflow-anchor: none; }}
:root{{color-scheme:dark;--bg:#030712;--bg-2:#07101d;--surface:rgba(12,21,37,.78);--surface-2:rgba(8,15,28,.86);--surface-3:rgba(17,29,49,.86);--border:rgba(148,163,184,.14);--border-strong:rgba(148,163,184,.22);--text:#f7f9ff;--muted:#8797b0;--muted-2:#617087;--blue:#79aaff;--cyan:#5de0df;--green:#62e6a4;--amber:#ffd273;--red:#ff838d;--violet:#a78bfa;--shadow:0 28px 70px rgba(0,0,0,.32);--shadow-soft:0 14px 36px rgba(0,0,0,.24)}}
*{{box-sizing:border-box}}
html{{scroll-behavior:smooth;background:var(--bg)}}
body{{font-family:Inter,ui-sans-serif,system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;margin:0;color:var(--text);min-height:100vh;font-variant-numeric:tabular-nums;background:radial-gradient(circle at 12% -8%,rgba(74,116,255,.22),transparent 31%),radial-gradient(circle at 88% 2%,rgba(41,211,205,.12),transparent 27%),linear-gradient(180deg,#030712 0%,#050b15 48%,#030711 100%)}}
body:before{{content:"";position:fixed;inset:0;pointer-events:none;background-image:linear-gradient(rgba(255,255,255,.014) 1px,transparent 1px),linear-gradient(90deg,rgba(255,255,255,.014) 1px,transparent 1px);background-size:38px 38px;mask-image:linear-gradient(to bottom,black,transparent 82%)}}
body:after{{content:"";position:fixed;width:500px;height:500px;right:-260px;top:22%;border-radius:50%;pointer-events:none;background:rgba(60,107,255,.055);filter:blur(60px)}}
main{{max-width:1580px;margin:auto;padding:18px 20px 48px;position:relative}}
h1,h2,h3{{margin:0}}
h1{{font-size:clamp(1.8rem,4vw,2.7rem);letter-spacing:-.045em;line-height:1.02}}
h2{{font-size:1.08rem;letter-spacing:-.02em}}
small,.muted{{color:var(--muted)}}
.premium-shell{{position:relative}}
.top-nav{{position:sticky;top:10px;z-index:30;display:flex;align-items:center;justify-content:space-between;gap:14px;margin-bottom:14px;padding:10px 12px;background:rgba(5,11,22,.72);border:1px solid rgba(148,163,184,.16);border-radius:17px;backdrop-filter:blur(22px) saturate(140%);box-shadow:0 14px 40px rgba(0,0,0,.26),inset 0 1px rgba(255,255,255,.03)}}
.brand{{display:flex;align-items:center;gap:10px;font-weight:850;letter-spacing:-.025em}}
.brand-mark{{width:32px;height:32px;border-radius:10px;display:grid;place-items:center;background:linear-gradient(135deg,#78a9ff,#5ce1d8);color:#03101d;box-shadow:0 0 28px rgba(91,189,255,.26);font-size:.76rem;letter-spacing:.02em}}
.nav-links{{display:flex;gap:5px;overflow:auto;scrollbar-width:none;padding:2px}}
.nav-links::-webkit-scrollbar{{display:none}}
.nav-links a{{color:#a8b7cc;text-decoration:none;font-size:.78rem;font-weight:700;padding:8px 10px;border-radius:10px;white-space:nowrap;border:1px solid transparent;transition:.18s ease}}
.nav-links a:hover{{background:rgba(255,255,255,.055);color:#fff;border-color:rgba(148,163,184,.1)}}
.card{{position:relative;overflow:hidden;background:linear-gradient(180deg,rgba(15,25,43,.84),rgba(7,14,27,.92));border:1px solid var(--border);border-radius:24px;padding:22px;box-shadow:0 32px 90px rgba(0,0,0,.38),inset 0 1px rgba(255,255,255,.035);backdrop-filter:blur(18px)}}
.card:before{{content:"";position:absolute;inset:0 0 auto;height:1px;background:linear-gradient(90deg,transparent,rgba(121,170,255,.55),rgba(93,224,223,.3),transparent)}}
.header{{display:flex;justify-content:space-between;gap:20px;align-items:flex-start;flex-wrap:wrap;padding:4px 2px 18px}}
.header-copy{{max-width:780px}}
.eyebrow{{display:flex;align-items:center;gap:8px;color:#9baeca;text-transform:uppercase;letter-spacing:.145em;font-size:.66rem;font-weight:850;margin-bottom:9px}}
.live-dot{{width:7px;height:7px;border-radius:50%;background:var(--green);box-shadow:0 0 0 5px rgba(99,230,163,.075),0 0 20px rgba(99,230,163,.72);animation:pulse-live 2.4s ease-in-out infinite}}
@keyframes pulse-live{{0%,100%{{opacity:1;transform:scale(1)}}50%{{opacity:.7;transform:scale(.86)}}}}
.header-subtitle{{display:block;margin-top:9px;font-size:.84rem;line-height:1.5}}
.header-meta{{display:flex;gap:8px;align-items:center;flex-wrap:wrap;justify-content:flex-end}}
.pill{{display:inline-flex;align-items:center;gap:7px;padding:8px 11px;border-radius:999px;background:rgba(255,255,255,.04);border:1px solid var(--border);font-size:.76rem;color:#c7d2e3;box-shadow:inset 0 1px rgba(255,255,255,.025)}}
.status-badge{{display:inline-flex;align-items:center;gap:7px;border-radius:999px;padding:7px 11px;font-size:.72rem;font-weight:850;border:1px solid;letter-spacing:.045em}}
.status-badge:before{{content:"";width:6px;height:6px;border-radius:50%;background:currentColor;box-shadow:0 0 12px currentColor}}
.status-ok{{color:#aef4cc;background:rgba(16,92,57,.24);border-color:rgba(99,230,163,.22)}}
.status-warn{{color:#ffe09c;background:rgba(130,91,12,.19);border-color:rgba(255,210,122,.22)}}
.status-error{{color:#ffb5bc;background:rgba(115,29,29,.22);border-color:rgba(255,138,138,.23)}}
.hero-kpis{{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:11px;margin:1px 0 18px}}
.hero-kpi{{position:relative;overflow:hidden;padding:16px 17px;border-radius:16px;background:linear-gradient(145deg,rgba(23,37,62,.88),rgba(7,16,31,.92));border:1px solid rgba(148,163,184,.13);box-shadow:var(--shadow-soft)}}
.hero-kpi:before{{content:"";position:absolute;inset:0 0 auto;height:1px;background:linear-gradient(90deg,rgba(121,170,255,.42),transparent 62%)}}
.hero-kpi:after{{content:"";position:absolute;width:130px;height:130px;right:-66px;top:-74px;border-radius:50%;background:rgba(101,160,255,.085);filter:blur(2px)}}
.hero-kpi small{{display:block;font-size:.66rem;text-transform:uppercase;letter-spacing:.1em;font-weight:800}}
.hero-kpi strong{{display:block;margin-top:7px;font-size:clamp(1.32rem,3vw,1.78rem);letter-spacing:-.035em;overflow-wrap:anywhere}}
.section{{position:relative;scroll-margin-top:78px;margin-top:13px;padding:17px;border:1px solid var(--border);border-radius:18px;background:linear-gradient(180deg,rgba(8,16,30,.68),rgba(6,13,25,.76));box-shadow:inset 0 1px rgba(255,255,255,.018)}}
.section-head{{display:flex;justify-content:space-between;align-items:end;gap:12px;margin-bottom:12px}}
.section-head h2{{display:flex;align-items:center;gap:8px}}
.section-head h2:before{{content:"";display:inline-block;width:5px;height:19px;border-radius:999px;background:linear-gradient(var(--blue),var(--cyan));box-shadow:0 0 18px rgba(96,176,255,.25)}}
.section-kicker{{font-size:.6rem;letter-spacing:.16em;font-weight:850;color:#7891b4;margin-bottom:5px}}
.metrics{{display:grid;grid-template-columns:repeat(auto-fit,minmax(155px,1fr));gap:9px}}
.metric{{background:linear-gradient(145deg,rgba(13,25,45,.8),rgba(7,15,29,.84));border:1px solid rgba(148,163,184,.105);border-radius:13px;padding:13px;min-width:0;transition:transform .18s ease,border-color .18s ease,background .18s ease}}
.metric:hover{{transform:translateY(-1px);border-color:rgba(113,167,255,.23);background:linear-gradient(145deg,rgba(18,32,55,.86),rgba(8,17,31,.88))}}
.metric small{{display:block;font-size:.69rem;text-transform:none}}
.metric strong{{display:block;font-size:1.15rem;margin-top:5px;letter-spacing:-.025em;overflow-wrap:anywhere}}
.metric.primary{{background:linear-gradient(145deg,rgba(29,55,91,.57),rgba(8,22,42,.86));border-color:rgba(113,167,255,.18)}}
.metric.primary strong{{font-size:1.42rem}}
.value-positive{{color:var(--green)!important}}
.value-negative{{color:var(--red)!important}}
.value-neutral{{color:var(--text)!important}}
.alert-box{{margin-top:12px;padding:12px 13px;border-radius:12px;background:rgba(9,19,35,.72);border:1px solid var(--border);font-size:.82rem}}
.alert-box.warn{{border-color:rgba(255,210,122,.27);background:rgba(87,62,9,.17);color:#ffe0a0}}
.runtime-reason{{display:block;margin-top:7px;line-height:1.45;font-size:.75rem}}
.portfolio-ribbon{{display:grid;grid-template-columns:repeat(8,minmax(0,1fr));gap:1px;margin:2px 0 14px;padding:1px;border-radius:15px;overflow:hidden;background:linear-gradient(90deg,rgba(121,170,255,.22),rgba(93,224,223,.14),rgba(167,139,250,.16));box-shadow:var(--shadow-soft)}}
.portfolio-ribbon>div{{padding:14px 15px;background:rgba(7,15,29,.94)}}
.portfolio-ribbon small{{display:block;font-size:.64rem;text-transform:uppercase;letter-spacing:.09em;margin-bottom:4px}}
.portfolio-ribbon strong{{font-size:1.04rem;letter-spacing:-.02em}}
.market-cards{{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:13px;margin-top:13px}}
.market-card{{--accent:var(--blue);--accent-soft:rgba(121,170,255,.11);position:relative;overflow:hidden;padding:16px;border:1px solid rgba(148,163,184,.13);border-radius:17px;background:linear-gradient(160deg,rgba(15,27,46,.92),rgba(6,13,25,.94));box-shadow:var(--shadow-soft);transition:transform .2s ease,border-color .2s ease,box-shadow .2s ease}}
.market-card:hover{{transform:translateY(-2px);border-color:color-mix(in srgb,var(--accent) 34%,transparent);box-shadow:0 20px 46px rgba(0,0,0,.3)}}
.market-card.gold{{--accent:#f6c76f;--accent-soft:rgba(246,199,111,.12)}}
.market-card.dax{{--accent:#7ea9ff;--accent-soft:rgba(126,169,255,.12)}}
.market-card.btc{{--accent:#f3a847;--accent-soft:rgba(243,168,71,.13)}}
.market-card-glow{{position:absolute;width:190px;height:190px;right:-100px;top:-110px;border-radius:50%;background:var(--accent-soft);filter:blur(3px);pointer-events:none}}
.market-card:before{{content:"";position:absolute;left:0;top:0;bottom:0;width:3px;background:linear-gradient(180deg,var(--accent),transparent 78%)}}
.market-card-head{{position:relative;display:flex;align-items:center;justify-content:space-between;gap:10px;margin-bottom:13px}}
.market-identity{{display:flex;align-items:center;gap:10px;min-width:0}}
.market-mark{{width:37px;height:37px;flex:0 0 37px;border-radius:11px;display:grid;place-items:center;font-weight:900;font-size:.76rem;color:var(--accent);background:var(--accent-soft);border:1px solid color-mix(in srgb,var(--accent) 24%,transparent);box-shadow:inset 0 1px rgba(255,255,255,.04)}}
.market-identity strong{{display:block;font-size:1.04rem;letter-spacing:-.025em}}
.market-identity small{{display:block;margin-top:2px;font-size:.68rem;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}}
.market-signal-row{{display:flex;align-items:center;justify-content:space-between;gap:10px;margin-bottom:8px}}
.signal-chip{{display:inline-flex;align-items:center;justify-content:center;min-width:66px;padding:6px 10px;border-radius:999px;font-size:.68rem;font-weight:900;letter-spacing:.065em;border:1px solid}}
.signal-long{{color:#aef5cc;background:rgba(34,197,94,.11);border-color:rgba(98,230,164,.23)}}
.signal-short{{color:#ffb6bd;background:rgba(239,68,68,.11);border-color:rgba(255,131,141,.23)}}
.signal-flat{{color:#c5d0df;background:rgba(148,163,184,.09);border-color:rgba(148,163,184,.17)}}
.signal-neutral{{color:#b8c6db;background:rgba(121,170,255,.08);border-color:rgba(121,170,255,.15)}}
.market-confidence-label{{font-size:.68rem;color:var(--muted)}}
.market-confidence-label strong{{color:#dbe7f7;margin-left:4px}}
.confidence-meter,.shadow-track{{height:5px;border-radius:999px;overflow:hidden;background:#07111f;border:1px solid rgba(148,163,184,.09)}}
.confidence-meter>span{{display:block;height:100%;border-radius:inherit;background:linear-gradient(90deg,var(--accent),var(--cyan));box-shadow:0 0 14px var(--accent-soft)}}
.market-grid{{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:8px;margin-top:12px}}
.market-grid div{{padding:10px;border-radius:11px;background:rgba(255,255,255,.024);border:1px solid rgba(148,163,184,.075)}}
.market-grid small{{display:block;color:var(--muted);font-size:.64rem;margin-bottom:4px}}
.market-grid strong{{font-size:.92rem;letter-spacing:-.01em}}
.shadow-row{{margin-top:12px;padding-top:11px;border-top:1px solid rgba(148,163,184,.08)}}
.shadow-row>div:first-child{{display:flex;justify-content:space-between;gap:10px;margin-bottom:6px;font-size:.67rem;color:var(--muted)}}
.shadow-row strong{{color:#cdd9e9;font-size:.67rem}}
.shadow-track>span{{display:block;height:100%;background:linear-gradient(90deg,var(--violet),var(--cyan));border-radius:inherit}}
.mtf-track>span{{background:linear-gradient(90deg,var(--blue),var(--green))}}
.market-card-footer{{display:flex;align-items:center;gap:9px;margin-top:11px;min-width:0}}
.market-card-footer small{{overflow:hidden;text-overflow:ellipsis;white-space:nowrap;font-size:.65rem}}
.gate-chip{{flex:0 0 auto;padding:5px 8px;border-radius:999px;font-size:.59rem;font-weight:850;letter-spacing:.06em;color:#c9bcff;background:rgba(167,139,250,.1);border:1px solid rgba(167,139,250,.18)}}
.readiness-grid{{display:grid;gap:7px;margin-top:12px}}
.readiness-row{{display:grid;grid-template-columns:minmax(145px,1.5fr) minmax(72px,.65fr) minmax(86px,.75fr) 68px;align-items:center;gap:9px;padding:10px 12px;border:1px solid rgba(148,163,184,.105);border-radius:11px;background:rgba(7,15,29,.68)}}
.criterion{{font-size:.8rem;font-weight:700;color:#d9e3f2}}
.criterion-value,.criterion-threshold{{font-size:.78rem;color:#9fb0c8;text-align:right}}
.criterion-status{{font-size:.68rem;text-align:center;padding:5px 7px;border-radius:999px;border:1px solid}}
.criterion-status.pass{{color:#bdf7d6;background:rgba(20,94,60,.28);border-color:rgba(99,230,163,.24)}}
.criterion-status.fail{{color:#ffc0c0;background:rgba(115,29,29,.26);border-color:rgba(255,138,138,.25)}}
.readiness-empty{{margin-top:12px;padding:14px;border:1px dashed #31425f;border-radius:11px;color:var(--muted);text-align:center;font-size:.78rem}}
.equity-chart{{margin-top:11px;background:linear-gradient(180deg,rgba(4,10,20,.9),rgba(7,15,28,.78));border:1px solid var(--border);border-radius:15px;padding:11px;overflow:hidden}}
.equity-chart svg{{display:block;width:100%;height:240px;filter:drop-shadow(0 12px 24px rgba(0,0,0,.22))}}
.chart-line{{fill:none;stroke-width:3.2;stroke-linecap:round;stroke-linejoin:round}}
.chart-line.positive{{stroke:var(--green)}}.chart-line.negative{{stroke:var(--red)}}
.chart-area{{opacity:.12}}.chart-area.positive{{fill:var(--green)}}.chart-area.negative{{fill:var(--red)}}
.chart-grid{{stroke:#293853;stroke-width:1}}
.chart-scale{{display:flex;justify-content:space-between;font-size:.72rem;color:var(--muted);margin-top:4px}}
.chart-empty{{margin-top:11px;padding:18px;border:1px dashed #31425f;border-radius:13px;color:var(--muted);text-align:center}}
.progress-track{{height:7px;background:#07101e;border:1px solid #24334d;border-radius:999px;overflow:hidden;margin-top:9px}}
.progress-fill{{height:100%;background:linear-gradient(90deg,#6d9eff,#60e1cd);border-radius:999px;box-shadow:0 0 16px rgba(96,225,205,.24)}}
.table-scroll{{overflow-x:auto;-webkit-overflow-scrolling:touch;margin-top:10px;border:1px solid var(--border);border-radius:14px;background:rgba(5,12,23,.7);box-shadow:inset 0 1px rgba(255,255,255,.02)}}
table{{width:100%;border-collapse:collapse;min-width:900px}}
th,td{{padding:12px 13px;border-bottom:1px solid rgba(148,163,184,.085);text-align:right;white-space:nowrap}}
th{{position:sticky;top:0;background:#0a1526;color:#9fafc7;font-size:.65rem;text-transform:uppercase;letter-spacing:.085em}}
td{{font-size:.8rem;color:#d8e1ef}}
th:first-child,td:first-child,th:nth-child(2),td:nth-child(2),th:nth-child(3),td:nth-child(3),th:last-child,td:last-child{{text-align:left}}
tbody tr{{transition:background .15s ease}}tbody tr:hover{{background:rgba(113,167,255,.045)}}
.footer-note{{text-align:center;color:#5e6f88;font-size:.68rem;padding:18px 4px 0;letter-spacing:.02em}}
@media (max-width:1080px){{.market-cards{{grid-template-columns:1fr}}.portfolio-ribbon{{grid-template-columns:repeat(2,minmax(0,1fr))}}}}
@media (max-width:900px){{.hero-kpis{{grid-template-columns:repeat(2,minmax(0,1fr))}}.nav-links{{max-width:60vw}}}}
@media (max-width:700px){{main{{padding:9px 8px 24px}}.top-nav{{top:5px;border-radius:13px;padding:8px 9px}}.brand span:last-child{{display:none}}.nav-links{{max-width:76vw}}.card{{padding:13px;border-radius:18px}}.header{{padding-bottom:13px}}.hero-kpis{{gap:8px}}.hero-kpi{{padding:13px 14px}}.metrics{{grid-template-columns:repeat(2,minmax(0,1fr))}}.metric{{padding:11px}}.metric strong{{font-size:1.02rem}}.metric.primary strong{{font-size:1.18rem}}.section{{padding:12px;border-radius:14px}}.portfolio-ribbon{{grid-template-columns:1fr 1fr}}.market-card{{padding:14px}}.readiness-row{{grid-template-columns:1fr auto;gap:6px 10px}}.criterion-value,.criterion-threshold{{text-align:left}}.criterion-status{{grid-column:2;grid-row:1 / span 2}}.criterion-threshold{{grid-column:1}}.equity-chart svg{{height:180px}}}}
@media (max-width:430px){{.hero-kpis{{grid-template-columns:1fr 1fr}}.hero-kpi{{padding:11px}}.hero-kpi strong{{font-size:1.1rem}}.metrics{{grid-template-columns:1fr 1fr}}.section-head{{align-items:flex-start;flex-direction:column;gap:4px}}.portfolio-ribbon{{grid-template-columns:1fr 1fr}}.portfolio-ribbon>div{{padding:11px}}.market-grid{{gap:7px}}}}
@media (prefers-reduced-motion:reduce){{*,*:before,*:after{{animation:none!important;transition:none!important;scroll-behavior:auto!important}}}}
</style></head><body><main>
<div class="premium-shell">
<nav class="top-nav" aria-label="Dashboard sections">
<div class="brand"><span class="brand-mark">AI</span><span>Trading Terminal</span></div>
<div class="nav-links">
<a href="#overview">Overview</a>
<a href="#scheduler">Scheduler</a>
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
<small class="header-subtitle">Premium read-only control center · live refresh without page jumps · durable hosted runtime</small>
</div>
<div class="header-meta">
<span class="pill">PAPER · READ ONLY</span>
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

{scheduler_panel}
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
<div class="metric"><small>PnL coverage</small><strong>{pnl_coverage_display}</strong></div>
<div class="metric"><small>Avg PnL / observed</small><strong>{average_pnl_display}</strong></div>
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
<script type="text/javascript">
(() => {{
  const REFRESH_MS = 2000;
  const INTERACTION_GRACE_MS = 1800;
  let refreshing = false;
  let lastInteractionAt = 0;

  const markInteraction = () => {{
    lastInteractionAt = Date.now();
  }};

  for (const eventName of ["scroll", "touchstart", "touchmove", "pointerdown", "wheel"]) {{
    window.addEventListener(eventName, markInteraction, {{passive: true}});
  }}

  function captureViewportAnchor() {{
    const candidates = Array.from(document.querySelectorAll("[id], .market-card, .section, .hero-kpi"));
    let best = null;
    let bestDistance = Number.POSITIVE_INFINITY;

    for (const element of candidates) {{
      const rect = element.getBoundingClientRect();
      if (rect.bottom <= 0 || rect.top >= window.innerHeight) continue;
      const distance = Math.abs(rect.top);
      if (distance < bestDistance) {{
        best = element;
        bestDistance = distance;
      }}
    }}

    if (!best) return null;

    const id = best.id || null;
    const marketLabel = best.classList.contains("market-card")
      ? best.querySelector(".market-card-head h3")?.textContent?.trim() || null
      : null;
    const sectionLabel = best.classList.contains("section")
      ? best.querySelector(".section-head h2")?.textContent?.trim() || null
      : null;

    return {{
      id,
      marketLabel,
      sectionLabel,
      top: best.getBoundingClientRect().top,
    }};
  }}

  function restoreViewportAnchor(anchor) {{
    if (!anchor) return;

    let element = null;
    if (anchor.id) {{
      element = document.getElementById(anchor.id);
    }}
    if (!element && anchor.marketLabel) {{
      element = Array.from(document.querySelectorAll(".market-card")).find(
        (card) => card.querySelector(".market-card-head h3")?.textContent?.trim() === anchor.marketLabel
      ) || null;
    }}
    if (!element && anchor.sectionLabel) {{
      element = Array.from(document.querySelectorAll(".section")).find(
        (section) => section.querySelector(".section-head h2")?.textContent?.trim() === anchor.sectionLabel
      ) || null;
    }}
    if (!element) return;

    const delta = element.getBoundingClientRect().top - anchor.top;
    if (Math.abs(delta) > 0.5) {{
      window.scrollBy({{left: 0, top: delta, behavior: "auto"}});
    }}
  }}

  async function refreshDashboard() {{
    if (refreshing || document.hidden) return;
    if (Date.now() - lastInteractionAt < INTERACTION_GRACE_MS) return;

    refreshing = true;
    const anchor = captureViewportAnchor();
    document.documentElement.classList.add("dashboard-refreshing");

    try {{
      const response = await fetch(window.location.href, {{
        cache: "no-store",
        headers: {{"X-Dashboard-Refresh": "1"}},
      }});
      if (!response.ok) throw new Error("dashboard refresh failed");

      const source = await response.text();
      const nextDocument = new DOMParser().parseFromString(source, "text/html");
      const currentCard = document.querySelector(".card");
      const nextCard = nextDocument.querySelector(".card");
      if (!currentCard || !nextCard) throw new Error("dashboard refresh markup missing");

      currentCard.replaceChildren(
        ...Array.from(nextCard.childNodes).map((node) => document.importNode(node, true))
      );

      requestAnimationFrame(() => {{
        restoreViewportAnchor(anchor);
        document.documentElement.classList.remove("dashboard-refreshing");
      }});
    }} catch (_) {{
      document.documentElement.classList.remove("dashboard-refreshing");
      // Keep the current dashboard visible if one refresh attempt fails.
    }} finally {{
      refreshing = false;
    }}
  }}

  window.setInterval(refreshDashboard, REFRESH_MS);
}})();
</script>
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
            mtf_period=effective_settings.mtf_period,
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
                    mtf_period=cycle_settings.mtf_period,
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
        server_version = "AITrading"
        sys_version = ""

        def end_headers(self) -> None:
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("X-Frame-Options", "DENY")
            self.send_header("Referrer-Policy", "no-referrer")
            self.send_header(
                "Permissions-Policy",
                "camera=(), microphone=(), geolocation=()",
            )
            self.send_header(
                "Content-Security-Policy",
                "default-src 'self'; base-uri 'none'; frame-ancestors 'none'; "
                "form-action 'none'; object-src 'none'; img-src 'self' data:; "
                "style-src 'self' 'unsafe-inline'; script-src 'self' 'unsafe-inline'; "
                "connect-src 'self'",
            )
            super().end_headers()

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
            if path == "/api/scheduler":
                try:
                    deliveries = backend.list_scheduler_deliveries(limit=20)
                    self._send_json(scheduler_delivery_overview(deliveries))
                except Exception:
                    self._send_json(
                        {
                            "storage_healthy": False,
                            "error": "scheduler telemetry unavailable",
                        },
                        status_code=503,
                    )
                return
            if path == "/api/status":
                self._send_json(load_status_snapshot())
                return
            if path == "/livez":
                self._send_json({"web_healthy": True})
                return
            if path == "/readyz":
                snapshot = load_status_snapshot()
                storage_healthy = snapshot.get("storage_healthy") is not False
                self._send_json(
                    {
                        "ready": storage_healthy,
                        "storage_healthy": storage_healthy,
                    }
                    if storage_healthy
                    else {
                        "ready": False,
                        "storage_healthy": False,
                        "error": "storage unavailable",
                    },
                    status_code=200 if storage_healthy else 503,
                )
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
            telemetry = scheduler_telemetry_payload(
                response,
                self.headers.get("X-Scheduler-Source"),
            )
            try:
                backend.record_scheduler_delivery(
                    SchedulerDelivery(
                        timestamp_utc=datetime.now(UTC).isoformat(),
                        source=str(telemetry["source"]),
                        status_code=int(telemetry["status_code"]),
                        ok=bool(telemetry["ok"]),
                        processed=(
                            int(telemetry["processed"])
                            if isinstance(telemetry.get("processed"), int)
                            and not isinstance(telemetry.get("processed"), bool)
                            else None
                        ),
                    )
                )
            except Exception:
                print(
                    json.dumps(
                        {
                            "event": "scheduler_delivery_persist_failed",
                            "source": telemetry["source"],
                        },
                        sort_keys=True,
                    ),
                    flush=True,
                )
            print(json.dumps(telemetry, sort_keys=True), flush=True)
            self._send_json(
                response.payload,
                status_code=response.status_code,
            )

        def log_message(self, format: str, *args: object) -> None:
            return

    ThreadingHTTPServer((host, port), Handler).serve_forever()

from ai_trading.dashboard import render_dashboard
from ai_trading.trade_journal import TradeJournal, TradeSnapshot


def test_trade_journal_round_trip(tmp_path) -> None:
    journal = TradeJournal(tmp_path / "trades.jsonl")
    trade = TradeSnapshot(
        timestamp_utc="2026-09-15T10:00:00+00:00",
        symbol="GC=F",
        side="BUY",
        quantity=0.25,
        price=3650.5,
        status="PAPER_FILLED",
        pnl=12.5,
        confidence=0.82,
        strategy="ai",
    )
    journal.append(trade)

    assert journal.list() == (trade,)


def test_dashboard_renders_trade_and_escapes_text(tmp_path) -> None:
    journal = TradeJournal(tmp_path / "trades.jsonl")
    journal.append(
        TradeSnapshot(
            timestamp_utc="2026-09-15T10:00:00+00:00",
            symbol="<GC>",
            side="BUY",
            quantity=0.25,
            price=3650.5,
            status="PAPER_FILLED",
            strategy="<script>",
        )
    )

    page = render_dashboard(journal)

    assert "&lt;GC&gt;" in page
    assert "&lt;script&gt;" in page
    assert "<script>" not in page
    assert "PAPER_FILLED" in page


def test_trade_journal_limit_returns_latest_events(tmp_path) -> None:
    journal = TradeJournal(tmp_path / "trades.jsonl")
    for index in range(3):
        journal.append(
            TradeSnapshot(
                timestamp_utc=f"2026-09-15T10:0{index}:00+00:00",
                symbol="GC=F",
                side="BUY",
                quantity=0.25,
                price=3650.0 + index,
                status="PAPER_FILLED",
            )
        )

    assert [trade.price for trade in journal.list(limit=2)] == [3651.0, 3652.0]


def test_dashboard_renders_portfolio_summary(tmp_path) -> None:
    journal = TradeJournal(tmp_path / "trades.jsonl")
    for pnl in (10.0, -4.0, 6.0):
        journal.append(
            TradeSnapshot(
                timestamp_utc="2026-09-15T10:00:00+00:00",
                symbol="GC=F",
                side="BUY",
                quantity=0.25,
                price=3650.0,
                status="PAPER_FILLED",
                pnl=pnl,
            )
        )

    page = render_dashboard(journal)

    assert "<strong>3</strong>" in page
    assert "<strong>12.00</strong>" in page
    assert "<strong>66.7%</strong>" in page
    assert "<strong>2 / 1</strong>" in page


def test_dashboard_renders_recent_trade_performance_metrics(tmp_path) -> None:
    journal = TradeJournal(tmp_path / "trades.jsonl")
    for pnl in (20.0, -5.0, -30.0, 10.0):
        journal.append(
            TradeSnapshot(
                timestamp_utc="2026-09-15T10:00:00+00:00",
                symbol="GC=F",
                side="BUY",
                quantity=0.25,
                price=3650.0,
                status="PAPER_FILLED",
                pnl=pnl,
            )
        )

    page = render_dashboard(journal)

    assert '<small>Avg PnL / trade</small><strong>-1.25</strong>' in page
    assert '<small>Profit factor</small><strong>0.86</strong>' in page
    assert '<small>Max realized DD</small><strong>35.00</strong>' in page
    assert "Performance window: latest 200 trade events" in page



def test_dashboard_renders_premium_terminal_shell(tmp_path) -> None:
    page = render_dashboard(TradeJournal(tmp_path / "empty.jsonl"))

    assert "premium-shell" in page
    assert "PAPER · READ ONLY" in page
    assert "live-dot" in page
    assert '<div class="portfolio-ribbon">' not in page
    assert "prefers-reduced-motion" in page



def test_dashboard_live_refresh_preserves_scroll_without_meta_reload(tmp_path) -> None:
    page = render_dashboard(TradeJournal(tmp_path / "empty.jsonl"))

    assert 'http-equiv="refresh"' not in page
    assert 'fetch(window.location.href' in page
    assert 'window.scrollTo({left: scrollX, top: scrollY' in page
    assert 'INTERACTION_GRACE_MS = 1800' in page
    assert 'touchmove' in page

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

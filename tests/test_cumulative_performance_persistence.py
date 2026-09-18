import os

import psycopg
import pytest

from ai_trading.file_persistence import FilePaperPersistence
from ai_trading.model_codec import serialize_model
from ai_trading.online import RiverDirectionModel
from ai_trading.persistence import CommitOutcome, RuntimeStepCommit
from ai_trading.runtime_state import RuntimeState
from ai_trading.trade_journal import TradeSnapshot

DATABASE_URL = os.environ["TEST_DATABASE_URL"]
RUNTIME_KEY = "paper:GC=F:5m:online-river:v1"


def _state(processed_bars: int) -> RuntimeState:
    return RuntimeState(
        cash=100_000.0,
        units=0.0,
        last_price=100.0,
        peak_equity=100_000.0,
        day_start_equity=100_000.0,
        last_processed=f"2026-09-18 10:{processed_bars:02d}:00+00:00",
        processed_bars=processed_bars,
        last_learning_cycle_bar=0,
    )


def _trade(pnl: float, index: int) -> TradeSnapshot:
    return TradeSnapshot(
        timestamp_utc=f"2026-09-18T10:{index:02d}:00+00:00",
        symbol="GC=F",
        side="BUY",
        quantity=1.0,
        price=100.0 + index,
        status="PAPER_FILLED",
        pnl=pnl,
        confidence=0.75,
        strategy="online-river",
    )


def _commit(revision: int, trade: TradeSnapshot) -> RuntimeStepCommit:
    return RuntimeStepCommit(
        expected_revision=revision,
        state=_state(revision + 1),
        model=serialize_model(RiverDirectionModel()),
        trade=trade,
        audit_event="runtime_step",
        audit_payload={"processed_bars": revision + 1},
    )


def _assert_metrics(metrics) -> None:
    assert metrics.trade_count == 4
    assert metrics.realized_pnl == pytest.approx(-5.0)
    assert metrics.average_pnl == pytest.approx(-1.25)
    assert metrics.gross_profit == pytest.approx(30.0)
    assert metrics.gross_loss == pytest.approx(35.0)
    assert metrics.profit_factor == pytest.approx(30.0 / 35.0)
    assert metrics.max_drawdown == pytest.approx(35.0)


def test_postgres_persists_cumulative_trade_performance() -> None:
    from ai_trading.postgres_persistence import PostgresPaperPersistence

    backend = PostgresPaperPersistence(DATABASE_URL)
    backend.initialize_schema()
    with psycopg.connect(DATABASE_URL) as connection, connection.cursor() as cursor:
        cursor.execute(
            "TRUNCATE paper_runtime_status, paper_audit_events, paper_trades, "
            "paper_model_state, paper_runtime_state RESTART IDENTITY CASCADE"
        )

    backend.load_runtime(RUNTIME_KEY, 100_000.0)
    for revision, pnl in enumerate((20.0, -5.0, -30.0, 10.0)):
        assert (
            backend.commit_step(RUNTIME_KEY, _commit(revision, _trade(pnl, revision)))
            is CommitOutcome.COMMITTED
        )

    _assert_metrics(backend.load_trade_performance(RUNTIME_KEY))


def test_postgres_duplicate_trade_does_not_double_count_performance() -> None:
    from ai_trading.postgres_persistence import PostgresPaperPersistence

    backend = PostgresPaperPersistence(DATABASE_URL)
    backend.initialize_schema()
    with psycopg.connect(DATABASE_URL) as connection, connection.cursor() as cursor:
        cursor.execute(
            "TRUNCATE paper_runtime_status, paper_audit_events, paper_trades, "
            "paper_model_state, paper_runtime_state RESTART IDENTITY CASCADE"
        )

    backend.load_runtime(RUNTIME_KEY, 100_000.0)
    trade = _trade(12.5, 0)
    assert backend.commit_step(RUNTIME_KEY, _commit(0, trade)) is CommitOutcome.COMMITTED
    assert backend.commit_step(RUNTIME_KEY, _commit(1, trade)) is CommitOutcome.COMMITTED

    metrics = backend.load_trade_performance(RUNTIME_KEY)
    assert metrics.trade_count == 1
    assert metrics.realized_pnl == pytest.approx(12.5)


def test_postgres_schema_initialization_backfills_missing_performance_summary() -> None:
    from ai_trading.postgres_persistence import PostgresPaperPersistence

    backend = PostgresPaperPersistence(DATABASE_URL)
    backend.initialize_schema()
    with psycopg.connect(DATABASE_URL) as connection, connection.cursor() as cursor:
        cursor.execute(
            "TRUNCATE paper_runtime_status, paper_audit_events, paper_trades, "
            "paper_model_state, paper_runtime_state RESTART IDENTITY CASCADE"
        )

    backend.load_runtime(RUNTIME_KEY, 100_000.0)
    for revision, pnl in enumerate((20.0, -5.0, -30.0, 10.0)):
        assert (
            backend.commit_step(RUNTIME_KEY, _commit(revision, _trade(pnl, revision)))
            is CommitOutcome.COMMITTED
        )

    with psycopg.connect(DATABASE_URL) as connection, connection.cursor() as cursor:
        cursor.execute(
            "DELETE FROM paper_trade_performance WHERE runtime_key = %s",
            (RUNTIME_KEY,),
        )

    backend.initialize_schema()
    _assert_metrics(backend.load_trade_performance(RUNTIME_KEY))


def test_file_backend_reports_full_journal_performance(tmp_path) -> None:
    backend = FilePaperPersistence(root=tmp_path)
    for index, pnl in enumerate((20.0, -5.0, -30.0, 10.0)):
        backend.trade_journal.append(_trade(pnl, index))

    _assert_metrics(backend.load_trade_performance(RUNTIME_KEY))

import os

import psycopg

from ai_trading.file_persistence import FilePaperPersistence
from ai_trading.model_codec import serialize_model
from ai_trading.online import RiverDirectionModel
from ai_trading.persistence import CommitOutcome, RuntimeStepCommit
from ai_trading.runtime_state import RuntimeState

DATABASE_URL = os.environ["TEST_DATABASE_URL"]
RUNTIME_KEY = "paper:GC=F:5m:online-river:v1"


def _commit(*, revision: int, cash: float, units: float, price: float) -> RuntimeStepCommit:
    processed_bars = revision + 1
    state = RuntimeState(
        cash=cash,
        units=units,
        last_price=price,
        peak_equity=100_000.0,
        day_start_equity=100_000.0,
        last_processed=f"2026-09-18 10:{processed_bars:02d}:00+00:00",
        processed_bars=processed_bars,
        last_learning_cycle_bar=0,
    )
    return RuntimeStepCommit(
        expected_revision=revision,
        state=state,
        model=serialize_model(RiverDirectionModel()),
        trade=None,
        audit_event="runtime_step",
        audit_payload={"processed_bars": processed_bars},
    )


def _assert_snapshots(snapshots) -> None:
    assert [snapshot.processed_bars for snapshot in snapshots] == [1, 2, 3]
    assert [snapshot.equity for snapshot in snapshots] == [100_000.0, 99_900.0, 100_300.0]
    assert all(snapshot.timestamp_utc for snapshot in snapshots)


def test_postgres_records_one_equity_snapshot_per_committed_bar() -> None:
    from ai_trading.postgres_persistence import PostgresPaperPersistence

    backend = PostgresPaperPersistence(DATABASE_URL)
    backend.initialize_schema()
    with psycopg.connect(DATABASE_URL) as connection, connection.cursor() as cursor:
        cursor.execute(
            "TRUNCATE paper_runtime_status, paper_audit_events, paper_trade_performance, "
            "paper_trades, paper_model_state, paper_runtime_state RESTART IDENTITY CASCADE"
        )

    backend.load_runtime(RUNTIME_KEY, 100_000.0)
    commits = (
        _commit(revision=0, cash=99_900.0, units=1.0, price=100.0),
        _commit(revision=1, cash=99_700.0, units=2.0, price=100.0),
        _commit(revision=2, cash=100_300.0, units=0.0, price=101.0),
    )
    for commit in commits:
        assert backend.commit_step(RUNTIME_KEY, commit) is CommitOutcome.COMMITTED

    _assert_snapshots(backend.list_burnin_snapshots(RUNTIME_KEY))


def test_postgres_conflict_does_not_append_burnin_snapshot() -> None:
    from ai_trading.postgres_persistence import PostgresPaperPersistence

    backend = PostgresPaperPersistence(DATABASE_URL)
    backend.initialize_schema()
    with psycopg.connect(DATABASE_URL) as connection, connection.cursor() as cursor:
        cursor.execute(
            "TRUNCATE paper_runtime_status, paper_audit_events, paper_trade_performance, "
            "paper_trades, paper_model_state, paper_runtime_state RESTART IDENTITY CASCADE"
        )

    backend.load_runtime(RUNTIME_KEY, 100_000.0)
    assert (
        backend.commit_step(
            RUNTIME_KEY,
            _commit(revision=0, cash=99_900.0, units=1.0, price=100.0),
        )
        is CommitOutcome.COMMITTED
    )
    assert (
        backend.commit_step(
            RUNTIME_KEY,
            _commit(revision=0, cash=99_800.0, units=2.0, price=100.0),
        )
        is CommitOutcome.CONFLICT
    )

    snapshots = backend.list_burnin_snapshots(RUNTIME_KEY)
    assert len(snapshots) == 1
    assert snapshots[0].processed_bars == 1


def test_file_backend_records_equity_snapshots_per_commit(tmp_path) -> None:
    backend = FilePaperPersistence(root=tmp_path)
    backend.load_runtime(RUNTIME_KEY, 100_000.0)

    commits = (
        _commit(revision=0, cash=99_900.0, units=1.0, price=100.0),
        _commit(revision=1, cash=99_700.0, units=2.0, price=100.0),
        _commit(revision=2, cash=100_300.0, units=0.0, price=101.0),
    )
    for commit in commits:
        assert backend.commit_step(RUNTIME_KEY, commit) is CommitOutcome.COMMITTED

    _assert_snapshots(backend.list_burnin_snapshots(RUNTIME_KEY))


def test_burnin_tracker_uses_processed_bars_for_readiness_duration(tmp_path) -> None:
    from ai_trading.burnin import BurnInTracker

    tracker = BurnInTracker(tmp_path / "burnin.jsonl")
    tracker.append(equity=100_000.0, processed_bars=125)
    tracker.append(equity=101_000.0, processed_bars=126)

    report = tracker.readiness()
    assert "insufficient burn-in duration" not in report.reasons

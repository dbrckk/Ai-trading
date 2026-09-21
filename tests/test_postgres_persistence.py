import os

import psycopg
import pytest

from ai_trading.model_codec import deserialize_model, serialize_model
from ai_trading.online import RiverDirectionModel
from ai_trading.persistence import CommitOutcome, RuntimeStepCommit, SchedulerDelivery
from ai_trading.runtime_state import RuntimeState
from ai_trading.runtime_status import HostedRuntimeStatus
from ai_trading.trade_journal import TradeSnapshot

DATABASE_URL = os.environ["TEST_DATABASE_URL"]
RUNTIME_KEY = "paper:GC=F:5m:online-river:v1"
BTC_RUNTIME_KEY = "paper:BTC-USD:5m:online-river:v1"
DAX_RUNTIME_KEY = "paper:^GDAXI:5m:online-river:v1"


def test_postgres_16_is_reachable() -> None:
    with psycopg.connect(DATABASE_URL) as connection, connection.cursor() as cursor:
        cursor.execute("SHOW server_version_num")
        assert int(cursor.fetchone()[0]) >= 160000


def _state(
    *,
    cash: float = 99_900.0,
    processed_bars: int = 1,
    average_entry_price: float = 100.0,
) -> RuntimeState:
    return RuntimeState(
        cash=cash,
        units=1.0,
        last_price=100.0,
        peak_equity=100_000.0,
        day_start_equity=100_000.0,
        average_entry_price=average_entry_price,
        last_processed="2026-09-15 10:00:00+00:00",
        processed_bars=processed_bars,
        last_learning_cycle_bar=0,
    )


def _trade(
    *,
    side: str = "BUY",
    pnl: float = 0.0,
    pnl_known: bool | None = None,
) -> TradeSnapshot:
    return TradeSnapshot(
        timestamp_utc="2026-09-15 10:00:00+00:00",
        symbol="GC=F",
        side=side,
        quantity=1.0,
        price=100.0,
        status="PAPER_FILLED",
        pnl=pnl,
        pnl_known=pnl_known,
        confidence=0.75,
        strategy="online-river",
    )


def _commit(
    *,
    expected_revision: int = 0,
    state: RuntimeState | None = None,
    trade: TradeSnapshot | None = None,
    observed_regime: str | None = None,
) -> RuntimeStepCommit:
    commit_state = state or _state()
    return RuntimeStepCommit(
        expected_revision=expected_revision,
        state=commit_state,
        model=serialize_model(RiverDirectionModel()),
        trade=trade,
        audit_event="runtime_step",
        audit_payload={"processed_bars": commit_state.processed_bars},
        observed_regime=observed_regime,
    )


@pytest.fixture
def backend():
    from ai_trading.postgres_persistence import PostgresPaperPersistence

    persistence = PostgresPaperPersistence(DATABASE_URL)
    persistence.initialize_schema()
    with psycopg.connect(DATABASE_URL) as connection, connection.cursor() as cursor:
        cursor.execute(
            "TRUNCATE paper_scheduler_deliveries, paper_runtime_status, "
            "paper_audit_events, paper_trades, paper_model_state, "
            "paper_runtime_state RESTART IDENTITY CASCADE"
        )
    return persistence


def test_schema_initialization_is_idempotent(backend) -> None:
    backend.initialize_schema()
    backend.initialize_schema()


def test_runtime_state_and_model_survive_new_instance(backend) -> None:
    from ai_trading.postgres_persistence import PostgresPaperPersistence

    fresh = backend.load_runtime(RUNTIME_KEY, 100_000.0)
    assert fresh.is_new is True
    assert fresh.revision == 0

    assert backend.commit_step(RUNTIME_KEY, _commit()) is CommitOutcome.COMMITTED

    restored = PostgresPaperPersistence(DATABASE_URL).load_runtime(RUNTIME_KEY, 100_000.0)
    assert restored.is_new is False
    assert restored.revision == 1
    assert restored.state.cash == 99_900.0
    assert restored.state.average_entry_price == 100.0
    assert restored.model is not None
    assert isinstance(deserialize_model(restored.model), RiverDirectionModel)


def test_fresh_instances_continue_from_persisted_revision(backend) -> None:
    from ai_trading.postgres_persistence import PostgresPaperPersistence

    backend.load_runtime(RUNTIME_KEY, 100_000.0)
    assert backend.commit_step(RUNTIME_KEY, _commit()) is CommitOutcome.COMMITTED

    restarted = PostgresPaperPersistence(DATABASE_URL)
    after_restart = restarted.load_runtime(RUNTIME_KEY, 100_000.0)
    assert after_restart.revision == 1
    assert after_restart.state.processed_bars == 1

    second_state = _state(cash=99_800.0, processed_bars=2)
    assert (
        restarted.commit_step(
            RUNTIME_KEY,
            _commit(expected_revision=after_restart.revision, state=second_state),
        )
        is CommitOutcome.COMMITTED
    )

    restored_again = PostgresPaperPersistence(DATABASE_URL).load_runtime(
        RUNTIME_KEY,
        100_000.0,
    )
    assert restored_again.revision == 2
    assert restored_again.state.cash == 99_800.0
    assert restored_again.state.processed_bars == 2
    assert restored_again.model is not None


def test_same_revision_has_exactly_one_winner(backend) -> None:
    backend.load_runtime(RUNTIME_KEY, 100_000.0)
    first = _commit(trade=_trade(side="BUY"))
    second = _commit(trade=_trade(side="SELL"))

    assert backend.commit_step(RUNTIME_KEY, first) is CommitOutcome.COMMITTED
    assert backend.commit_step(RUNTIME_KEY, second) is CommitOutcome.CONFLICT

    restored = backend.load_runtime(RUNTIME_KEY, 100_000.0)
    assert restored.revision == 1
    trades = backend.list_trades(RUNTIME_KEY)
    assert len(trades) == 1
    assert trades[0].side == "BUY"


def test_duplicate_logical_trade_is_idempotent_across_revisions(backend) -> None:
    backend.load_runtime(RUNTIME_KEY, 100_000.0)
    trade = _trade()

    assert backend.commit_step(RUNTIME_KEY, _commit(trade=trade)) is CommitOutcome.COMMITTED
    assert (
        backend.commit_step(
            RUNTIME_KEY,
            _commit(
                expected_revision=1,
                state=_state(cash=99_800.0, processed_bars=2),
                trade=trade,
            ),
        )
        is CommitOutcome.COMMITTED
    )

    restored = backend.load_runtime(RUNTIME_KEY, 100_000.0)
    assert restored.revision == 2
    assert restored.state.cash == 99_800.0
    assert backend.list_trades(RUNTIME_KEY) == (trade,)


def test_failure_before_state_commit_rolls_back_everything(backend) -> None:
    from ai_trading.postgres_persistence import PostgresPaperPersistence

    backend.load_runtime(RUNTIME_KEY, 100_000.0)

    def fail() -> None:
        raise RuntimeError("forced transaction failure")

    failing = PostgresPaperPersistence(DATABASE_URL, before_state_commit=fail)
    with pytest.raises(RuntimeError, match="forced transaction failure"):
        failing.commit_step(RUNTIME_KEY, _commit(trade=_trade()))

    restored = backend.load_runtime(RUNTIME_KEY, 100_000.0)
    assert restored.revision == 0
    assert restored.model is None
    assert backend.list_trades(RUNTIME_KEY) == ()
    with psycopg.connect(DATABASE_URL) as connection, connection.cursor() as cursor:
        cursor.execute(
            "SELECT count(*) FROM paper_audit_events WHERE runtime_key = %s",
            (RUNTIME_KEY,),
        )
        assert cursor.fetchone()[0] == 0


def test_runtime_status_survives_new_instance(backend) -> None:
    from ai_trading.postgres_persistence import PostgresPaperPersistence

    status = HostedRuntimeStatus(
        engine_status="RUNNING",
        symbol="GC=F",
        interval="5m",
        updated_at_utc="2026-09-15T20:00:00+00:00",
        processed=True,
        equity=100_123.0,
        poll_seconds=120.0,
    )
    backend.save_runtime_status(RUNTIME_KEY, status)

    restored = PostgresPaperPersistence(DATABASE_URL).load_runtime_status(RUNTIME_KEY)
    assert restored == status


def test_regime_coverage_is_deduplicated_and_persisted(backend) -> None:
    backend.load_runtime(RUNTIME_KEY, 100_000.0)

    assert (
        backend.commit_step(
            RUNTIME_KEY,
            _commit(observed_regime="bull_normal_vol"),
        )
        is CommitOutcome.COMMITTED
    )
    assert (
        backend.commit_step(
            RUNTIME_KEY,
            _commit(
                expected_revision=1,
                state=_state(cash=99_800.0, processed_bars=2),
                observed_regime="bull_normal_vol",
            ),
        )
        is CommitOutcome.COMMITTED
    )
    assert (
        backend.commit_step(
            RUNTIME_KEY,
            _commit(
                expected_revision=2,
                state=_state(cash=99_700.0, processed_bars=3),
                observed_regime="sideways_normal_vol",
            ),
        )
        is CommitOutcome.COMMITTED
    )

    assert backend.list_regimes(RUNTIME_KEY) == (
        "bull_normal_vol",
        "sideways_normal_vol",
    )
    snapshots = backend.list_burnin_snapshots(RUNTIME_KEY)
    assert snapshots[-1].regimes_covered == 2



def test_postgres_loads_shadow_quality_from_audit(backend) -> None:
    backend.load_runtime(RUNTIME_KEY, 100_000.0)
    commit = _commit()
    shadow_commit = RuntimeStepCommit(
        expected_revision=commit.expected_revision,
        state=commit.state,
        model=commit.model,
        trade=commit.trade,
        audit_event=commit.audit_event,
        audit_payload={
            "prediction": {"side": 1, "confidence": 0.80},
            "shadow_challenger": {
                "prediction": {"side": 0, "confidence": 0.70},
                "realized_label": 0,
            },
        },
        observed_regime=commit.observed_regime,
    )

    assert backend.commit_step(RUNTIME_KEY, shadow_commit) is CommitOutcome.COMMITTED
    comparison = backend.load_shadow_quality(RUNTIME_KEY)

    assert comparison.observations == 1
    assert comparison.river.observations == 1
    assert comparison.challenger.observations == 1


def test_scheduler_deliveries_survive_postgres_restart(backend) -> None:
    from ai_trading.postgres_persistence import PostgresPaperPersistence

    delivery = SchedulerDelivery(
        timestamp_utc="2026-09-21T16:05:00+00:00",
        source="cloudflare",
        status_code=200,
        ok=True,
        processed=1,
    )
    backend.record_scheduler_delivery(delivery)

    restored = PostgresPaperPersistence(DATABASE_URL)
    assert restored.list_scheduler_deliveries(limit=10) == (delivery,)



def test_postgres_persists_pnl_provenance_and_performance_coverage(backend) -> None:
    backend.load_runtime(RUNTIME_KEY, 100_000.0)

    known = _trade(side="BUY", pnl=5.0, pnl_known=True)
    unknown = _trade(side="SELL", pnl=0.0, pnl_known=False)

    assert (
        backend.commit_step(
            RUNTIME_KEY,
            _commit(
                expected_revision=0,
                state=_state(processed_bars=1, average_entry_price=101.5),
                trade=known,
            ),
        )
        is CommitOutcome.COMMITTED
    )
    assert (
        backend.commit_step(
            RUNTIME_KEY,
            _commit(
                expected_revision=1,
                state=_state(
                    cash=99_800.0,
                    processed_bars=2,
                    average_entry_price=0.0,
                ),
                trade=unknown,
            ),
        )
        is CommitOutcome.COMMITTED
    )

    restored = backend.load_runtime(RUNTIME_KEY, 100_000.0)
    assert restored.state.average_entry_price == 0.0

    trades = backend.list_trades(RUNTIME_KEY)
    assert trades[0].pnl == 5.0
    assert trades[0].pnl_known is True
    assert trades[1].pnl == 0.0
    assert trades[1].pnl_known is False

    metrics = backend.load_trade_performance(RUNTIME_KEY)
    assert metrics.trade_count == 2
    assert metrics.pnl_observations == 1
    assert metrics.realized_pnl == 5.0
    assert metrics.average_pnl == 5.0
    assert metrics.gross_profit == 5.0
    assert metrics.gross_loss == 0.0
    assert metrics.profit_factor == float("inf")


def test_trade_event_key_ignores_pnl_provenance_metadata() -> None:
    from ai_trading.postgres_persistence import _trade_event_key

    known = _trade(pnl=0.0, pnl_known=True)
    unknown = _trade(pnl=0.0, pnl_known=False)

    assert _trade_event_key(known) == _trade_event_key(unknown)



def test_schema_upgrade_adds_pnl_accounting_columns_without_reset(backend) -> None:
    with psycopg.connect(DATABASE_URL) as connection, connection.cursor() as cursor:
        cursor.execute(
            "ALTER TABLE paper_trade_performance "
            "DROP COLUMN IF EXISTS pnl_observations"
        )
        cursor.execute("ALTER TABLE paper_trades DROP COLUMN IF EXISTS pnl_known")
        cursor.execute(
            "ALTER TABLE paper_runtime_state "
            "DROP COLUMN IF EXISTS average_entry_price"
        )

    backend.initialize_schema()

    with psycopg.connect(DATABASE_URL) as connection, connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT table_name, column_name
            FROM information_schema.columns
            WHERE (table_name, column_name) IN (
                ('paper_runtime_state', 'average_entry_price'),
                ('paper_trades', 'pnl_known'),
                ('paper_trade_performance', 'pnl_observations')
            )
            ORDER BY table_name, column_name
            """
        )
        columns = {(row[0], row[1]) for row in cursor.fetchall()}

    assert columns == {
        ("paper_runtime_state", "average_entry_price"),
        ("paper_trade_performance", "pnl_observations"),
        ("paper_trades", "pnl_known"),
    }



def test_postgres_portfolio_performance_uses_global_trade_chronology(backend) -> None:
    backend.load_runtime(RUNTIME_KEY, 100_000.0)
    backend.load_runtime(BTC_RUNTIME_KEY, 100_000.0)
    backend.load_runtime(DAX_RUNTIME_KEY, 100_000.0)

    assert (
        backend.commit_step(
            RUNTIME_KEY,
            _commit(
                expected_revision=0,
                state=_state(processed_bars=1),
                trade=_trade(pnl=10.0, pnl_known=True),
            ),
        )
        is CommitOutcome.COMMITTED
    )
    assert (
        backend.commit_step(
            BTC_RUNTIME_KEY,
            _commit(
                expected_revision=0,
                state=_state(processed_bars=1),
                trade=_trade(pnl=-20.0, pnl_known=True),
            ),
        )
        is CommitOutcome.COMMITTED
    )
    assert (
        backend.commit_step(
            RUNTIME_KEY,
            _commit(
                expected_revision=1,
                state=_state(cash=99_800.0, processed_bars=2),
                trade=_trade(pnl=5.0, pnl_known=True),
            ),
        )
        is CommitOutcome.COMMITTED
    )
    assert (
        backend.commit_step(
            BTC_RUNTIME_KEY,
            _commit(
                expected_revision=1,
                state=_state(cash=99_800.0, processed_bars=2),
                trade=_trade(pnl=0.0, pnl_known=False),
            ),
        )
        is CommitOutcome.COMMITTED
    )
    assert (
        backend.commit_step(
            DAX_RUNTIME_KEY,
            _commit(
                expected_revision=0,
                state=_state(processed_bars=1),
                trade=_trade(pnl=1000.0, pnl_known=True),
            ),
        )
        is CommitOutcome.COMMITTED
    )

    metrics = backend.load_portfolio_trade_performance(
        (RUNTIME_KEY, BTC_RUNTIME_KEY)
    )

    assert metrics.trade_count == 4
    assert metrics.pnl_observations == 3
    assert metrics.realized_pnl == -5.0
    assert metrics.average_pnl == pytest.approx(-5.0 / 3.0)
    assert metrics.gross_profit == 15.0
    assert metrics.gross_loss == 20.0
    assert metrics.profit_factor == pytest.approx(0.75)
    assert metrics.max_drawdown == 20.0


def test_postgres_portfolio_performance_empty_runtime_set_is_empty(backend) -> None:
    metrics = backend.load_portfolio_trade_performance(())

    assert metrics.trade_count == 0
    assert metrics.pnl_observations == 0
    assert metrics.realized_pnl == 0.0
    assert metrics.profit_factor is None
    assert metrics.max_drawdown == 0.0

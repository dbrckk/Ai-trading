import os

import psycopg
import pytest

from ai_trading.model_codec import serialize_model
from ai_trading.online import RiverDirectionModel
from ai_trading.persistence import CommitOutcome, RuntimeStepCommit
from ai_trading.runtime_state import RuntimeState
from ai_trading.runtime_status import HostedRuntimeStatus
from ai_trading.trade_journal import TradeSnapshot

DATABASE_URL = os.environ["TEST_DATABASE_URL"]
RUNTIME_KEY = "paper:GC=F:5m:online-river:v1"


def _state(*, cash: float = 99_900.0, processed_bars: int = 1) -> RuntimeState:
    return RuntimeState(
        cash=cash,
        units=1.0,
        last_price=100.0,
        peak_equity=100_000.0,
        day_start_equity=100_000.0,
        last_processed="2026-09-15 10:00:00+00:00",
        processed_bars=processed_bars,
        last_learning_cycle_bar=0,
    )


def _trade(*, side: str = "BUY") -> TradeSnapshot:
    return TradeSnapshot(
        timestamp_utc="2026-09-15 10:00:00+00:00",
        symbol="GC=F",
        side=side,
        quantity=1.0,
        price=100.0,
        status="PAPER_FILLED",
        confidence=0.75,
        strategy="online-river",
    )


def _commit(
    *,
    expected_revision: int = 0,
    state: RuntimeState | None = None,
    trade: TradeSnapshot | None = None,
) -> RuntimeStepCommit:
    return RuntimeStepCommit(
        expected_revision=expected_revision,
        state=state or _state(),
        model=serialize_model(RiverDirectionModel()),
        trade=trade,
        audit_event="runtime_step",
        audit_payload={"processed_bars": (state or _state()).processed_bars},
    )


@pytest.fixture
def backend():
    from ai_trading.postgres_persistence import PostgresPaperPersistence

    persistence = PostgresPaperPersistence(DATABASE_URL)
    persistence.initialize_schema()
    with psycopg.connect(DATABASE_URL) as connection, connection.cursor() as cursor:
        cursor.execute(
            "TRUNCATE paper_runtime_status, paper_audit_events, paper_trades, "
            "paper_model_state, paper_runtime_state RESTART IDENTITY CASCADE"
        )
    return persistence


def test_schema_initialization_is_idempotent(backend) -> None:
    backend.initialize_schema()
    backend.initialize_schema()


def test_runtime_state_and_model_survive_new_instance(backend) -> None:
    from ai_trading.model_codec import deserialize_model
    from ai_trading.postgres_persistence import PostgresPaperPersistence

    fresh = backend.load_runtime(RUNTIME_KEY, 100_000.0)
    assert fresh.is_new is True
    assert fresh.revision == 0

    assert backend.commit_step(RUNTIME_KEY, _commit()) is CommitOutcome.COMMITTED

    restored = PostgresPaperPersistence(DATABASE_URL).load_runtime(RUNTIME_KEY, 100_000.0)
    assert restored.is_new is False
    assert restored.revision == 1
    assert restored.state.cash == 99_900.0
    assert restored.model is not None
    assert isinstance(deserialize_model(restored.model), RiverDirectionModel)


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

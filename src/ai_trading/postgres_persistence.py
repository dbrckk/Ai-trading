from __future__ import annotations

import hashlib
import json
from collections.abc import Callable
from dataclasses import asdict

import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from .audit import build_audit_record
from .burnin import BurnInSnapshot
from .performance_metrics import (
    TradePerformanceMetrics,
    performance_metrics_from_totals,
)
from .persistence import (
    CommitOutcome,
    ModelBlob,
    PaperPersistence,
    PersistedRuntime,
    RuntimeStepCommit,
)
from .runtime_state import RuntimeState
from .runtime_status import HostedRuntimeStatus
from .trade_journal import TradeSnapshot

_SCHEMA_STATEMENTS = (
    """
    CREATE TABLE IF NOT EXISTS paper_runtime_state (
        runtime_key text PRIMARY KEY,
        cash double precision NOT NULL,
        units double precision NOT NULL,
        last_price double precision NOT NULL,
        peak_equity double precision NOT NULL,
        day_start_equity double precision NOT NULL,
        last_processed text NULL,
        processed_bars bigint NOT NULL,
        last_learning_cycle_bar bigint NOT NULL,
        revision bigint NOT NULL DEFAULT 0,
        updated_at timestamptz NOT NULL DEFAULT now()
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS paper_model_state (
        runtime_key text PRIMARY KEY
            REFERENCES paper_runtime_state(runtime_key) ON DELETE CASCADE,
        format text NOT NULL,
        version integer NOT NULL,
        payload bytea NOT NULL,
        sha256 text NOT NULL,
        updated_at timestamptz NOT NULL DEFAULT now()
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS paper_trades (
        id bigserial PRIMARY KEY,
        runtime_key text NOT NULL
            REFERENCES paper_runtime_state(runtime_key) ON DELETE CASCADE,
        event_key text NOT NULL,
        timestamp_utc text NOT NULL,
        symbol text NOT NULL,
        side text NOT NULL,
        quantity double precision NOT NULL,
        price double precision NOT NULL,
        status text NOT NULL,
        pnl double precision NOT NULL DEFAULT 0,
        confidence double precision NULL,
        strategy text NOT NULL,
        created_at timestamptz NOT NULL DEFAULT now(),
        UNIQUE (runtime_key, event_key)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS paper_trade_performance (
        runtime_key text PRIMARY KEY
            REFERENCES paper_runtime_state(runtime_key) ON DELETE CASCADE,
        trade_count bigint NOT NULL DEFAULT 0,
        realized_pnl double precision NOT NULL DEFAULT 0,
        gross_profit double precision NOT NULL DEFAULT 0,
        gross_loss double precision NOT NULL DEFAULT 0,
        peak_realized_pnl double precision NOT NULL DEFAULT 0,
        max_drawdown double precision NOT NULL DEFAULT 0,
        updated_at timestamptz NOT NULL DEFAULT now()
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS paper_burnin_snapshots (
        runtime_key text NOT NULL
            REFERENCES paper_runtime_state(runtime_key) ON DELETE CASCADE,
        processed_bars bigint NOT NULL,
        timestamp_utc text NOT NULL,
        equity double precision NOT NULL,
        scheduler_errors integer NOT NULL DEFAULT 0,
        regimes_covered integer NOT NULL DEFAULT 0,
        bootstrap_probability_positive double precision NOT NULL DEFAULT 0,
        created_at timestamptz NOT NULL DEFAULT now(),
        PRIMARY KEY (runtime_key, processed_bars)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS paper_audit_events (
        id bigserial PRIMARY KEY,
        runtime_key text NOT NULL
            REFERENCES paper_runtime_state(runtime_key) ON DELETE CASCADE,
        timestamp_utc timestamptz NOT NULL,
        event text NOT NULL,
        payload jsonb NOT NULL,
        prev_hash text NOT NULL,
        hash text NOT NULL,
        UNIQUE (runtime_key, hash)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS paper_runtime_status (
        runtime_key text PRIMARY KEY,
        engine_status text NOT NULL,
        symbol text NOT NULL,
        interval text NOT NULL,
        updated_at_utc timestamptz NOT NULL,
        payload jsonb NOT NULL
    )
    """,
    """
    CREATE INDEX IF NOT EXISTS paper_trades_runtime_id_idx
        ON paper_trades (runtime_key, id DESC)
    """,
    """
    CREATE INDEX IF NOT EXISTS paper_audit_runtime_id_idx
        ON paper_audit_events (runtime_key, id DESC)
    """,
    """
    CREATE INDEX IF NOT EXISTS paper_burnin_runtime_bars_idx
        ON paper_burnin_snapshots (runtime_key, processed_bars)
    """,
    """
    INSERT INTO paper_burnin_snapshots (
        runtime_key,
        processed_bars,
        timestamp_utc,
        equity
    )
    SELECT
        runtime_key,
        processed_bars,
        COALESCE(last_processed, updated_at::text),
        cash + units * last_price
    FROM paper_runtime_state
    WHERE processed_bars > 0
    ON CONFLICT (runtime_key, processed_bars) DO NOTHING
    """,
    """
    WITH source AS (
        SELECT t.runtime_key, t.id, t.pnl
        FROM paper_trades AS t
        WHERE NOT EXISTS (
            SELECT 1
            FROM paper_trade_performance AS p
            WHERE p.runtime_key = t.runtime_key
        )
    ),
    curve AS (
        SELECT
            runtime_key,
            id,
            pnl,
            SUM(pnl) OVER (
                PARTITION BY runtime_key
                ORDER BY id
                ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
            ) AS cumulative_pnl
        FROM source
    ),
    peaks AS (
        SELECT
            runtime_key,
            id,
            pnl,
            cumulative_pnl,
            MAX(GREATEST(cumulative_pnl, 0.0)) OVER (
                PARTITION BY runtime_key
                ORDER BY id
                ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
            ) AS running_peak
        FROM curve
    ),
    summary AS (
        SELECT
            runtime_key,
            COUNT(*) AS trade_count,
            SUM(pnl) AS realized_pnl,
            SUM(CASE WHEN pnl > 0 THEN pnl ELSE 0 END) AS gross_profit,
            -SUM(CASE WHEN pnl < 0 THEN pnl ELSE 0 END) AS gross_loss,
            MAX(running_peak) AS peak_realized_pnl,
            MAX(running_peak - cumulative_pnl) AS max_drawdown
        FROM peaks
        GROUP BY runtime_key
    )
    INSERT INTO paper_trade_performance (
        runtime_key,
        trade_count,
        realized_pnl,
        gross_profit,
        gross_loss,
        peak_realized_pnl,
        max_drawdown
    )
    SELECT
        runtime_key,
        trade_count,
        realized_pnl,
        gross_profit,
        gross_loss,
        peak_realized_pnl,
        max_drawdown
    FROM summary
    ON CONFLICT (runtime_key) DO NOTHING
    """,
)


def _trade_event_key(trade: TradeSnapshot) -> str:
    canonical = json.dumps(
        asdict(trade),
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


class PostgresPaperPersistence(PaperPersistence):
    def __init__(
        self,
        database_url: str,
        *,
        before_state_commit: Callable[[], None] | None = None,
    ) -> None:
        self.database_url = database_url
        self.before_state_commit = before_state_commit

    def _connect(self):
        return psycopg.connect(self.database_url, row_factory=dict_row)

    def initialize_schema(self) -> None:
        with self._connect() as connection, connection.cursor() as cursor:
            for statement in _SCHEMA_STATEMENTS:
                cursor.execute(statement)

    def load_runtime(self, runtime_key: str, starting_cash: float) -> PersistedRuntime:
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO paper_runtime_state (
                    runtime_key, cash, units, last_price, peak_equity,
                    day_start_equity, last_processed, processed_bars,
                    last_learning_cycle_bar, revision
                )
                VALUES (%s, %s, 0, 0, %s, %s, NULL, 0, 0, 0)
                ON CONFLICT (runtime_key) DO NOTHING
                RETURNING runtime_key
                """,
                (runtime_key, starting_cash, starting_cash, starting_cash),
            )
            is_new = cursor.fetchone() is not None

            cursor.execute(
                """
                SELECT cash, units, last_price, peak_equity, day_start_equity,
                       last_processed, processed_bars, last_learning_cycle_bar, revision
                FROM paper_runtime_state
                WHERE runtime_key = %s
                """,
                (runtime_key,),
            )
            row = cursor.fetchone()
            if row is None:
                raise RuntimeError("runtime state missing after initialization")

            cursor.execute(
                """
                SELECT format, version, payload, sha256
                FROM paper_model_state
                WHERE runtime_key = %s
                """,
                (runtime_key,),
            )
            model_row = cursor.fetchone()

        state = RuntimeState(
            cash=float(row["cash"]),
            units=float(row["units"]),
            last_price=float(row["last_price"]),
            peak_equity=float(row["peak_equity"]),
            day_start_equity=float(row["day_start_equity"]),
            last_processed=row["last_processed"],
            processed_bars=int(row["processed_bars"]),
            last_learning_cycle_bar=int(row["last_learning_cycle_bar"]),
        )
        model = None
        if model_row is not None:
            model = ModelBlob(
                format=str(model_row["format"]),
                version=int(model_row["version"]),
                payload=bytes(model_row["payload"]),
                sha256=str(model_row["sha256"]),
            )
        return PersistedRuntime(
            state=state,
            model=model,
            revision=int(row["revision"]),
            is_new=is_new,
        )

    def commit_step(self, runtime_key: str, commit: RuntimeStepCommit) -> CommitOutcome:
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                "SELECT revision FROM paper_runtime_state WHERE runtime_key = %s FOR UPDATE",
                (runtime_key,),
            )
            current = cursor.fetchone()
            if current is None:
                raise RuntimeError("runtime state missing")
            if int(current["revision"]) != commit.expected_revision:
                return CommitOutcome.CONFLICT

            if commit.trade is not None:
                trade = commit.trade
                cursor.execute(
                    """
                    INSERT INTO paper_trades (
                        runtime_key, event_key, timestamp_utc, symbol, side,
                        quantity, price, status, pnl, confidence, strategy
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (runtime_key, event_key) DO NOTHING
                    RETURNING id
                    """,
                    (
                        runtime_key,
                        _trade_event_key(trade),
                        trade.timestamp_utc,
                        trade.symbol,
                        trade.side,
                        trade.quantity,
                        trade.price,
                        trade.status,
                        trade.pnl,
                        trade.confidence,
                        trade.strategy,
                    ),
                )
                trade_inserted = cursor.fetchone() is not None
                if trade_inserted:
                    pnl = float(trade.pnl)
                    cursor.execute(
                        """
                        INSERT INTO paper_trade_performance (
                            runtime_key,
                            trade_count,
                            realized_pnl,
                            gross_profit,
                            gross_loss,
                            peak_realized_pnl,
                            max_drawdown,
                            updated_at
                        )
                        VALUES (
                            %s,
                            1,
                            %s,
                            GREATEST(%s, 0.0),
                            GREATEST(-%s, 0.0),
                            GREATEST(%s, 0.0),
                            GREATEST(-%s, 0.0),
                            now()
                        )
                        ON CONFLICT (runtime_key) DO UPDATE SET
                            trade_count = paper_trade_performance.trade_count + 1,
                            realized_pnl = (
                                paper_trade_performance.realized_pnl
                                + EXCLUDED.realized_pnl
                            ),
                            gross_profit = (
                                paper_trade_performance.gross_profit
                                + EXCLUDED.gross_profit
                            ),
                            gross_loss = (
                                paper_trade_performance.gross_loss
                                + EXCLUDED.gross_loss
                            ),
                            peak_realized_pnl = GREATEST(
                                paper_trade_performance.peak_realized_pnl,
                                paper_trade_performance.realized_pnl
                                + EXCLUDED.realized_pnl
                            ),
                            max_drawdown = GREATEST(
                                paper_trade_performance.max_drawdown,
                                GREATEST(
                                    paper_trade_performance.peak_realized_pnl,
                                    paper_trade_performance.realized_pnl
                                    + EXCLUDED.realized_pnl
                                )
                                - (
                                    paper_trade_performance.realized_pnl
                                    + EXCLUDED.realized_pnl
                                )
                            ),
                            updated_at = now()
                        """,
                        (runtime_key, pnl, pnl, pnl, pnl, pnl),
                    )

            cursor.execute(
                """
                SELECT hash FROM paper_audit_events
                WHERE runtime_key = %s
                ORDER BY id DESC
                LIMIT 1
                """,
                (runtime_key,),
            )
            previous = cursor.fetchone()
            previous_hash = "GENESIS" if previous is None else str(previous["hash"])
            audit = build_audit_record(
                commit.audit_event,
                commit.audit_payload,
                previous_hash,
            )
            cursor.execute(
                """
                INSERT INTO paper_audit_events (
                    runtime_key, timestamp_utc, event, payload, prev_hash, hash
                )
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (
                    runtime_key,
                    audit["timestamp_utc"],
                    audit["event"],
                    Jsonb(audit["payload"]),
                    audit["prev_hash"],
                    audit["hash"],
                ),
            )

            cursor.execute(
                """
                INSERT INTO paper_model_state (
                    runtime_key, format, version, payload, sha256, updated_at
                )
                VALUES (%s, %s, %s, %s, %s, now())
                ON CONFLICT (runtime_key) DO UPDATE SET
                    format = EXCLUDED.format,
                    version = EXCLUDED.version,
                    payload = EXCLUDED.payload,
                    sha256 = EXCLUDED.sha256,
                    updated_at = now()
                """,
                (
                    runtime_key,
                    commit.model.format,
                    commit.model.version,
                    commit.model.payload,
                    commit.model.sha256,
                ),
            )

            if self.before_state_commit is not None:
                self.before_state_commit()

            state = commit.state
            cursor.execute(
                """
                UPDATE paper_runtime_state
                SET cash = %s,
                    units = %s,
                    last_price = %s,
                    peak_equity = %s,
                    day_start_equity = %s,
                    last_processed = %s,
                    processed_bars = %s,
                    last_learning_cycle_bar = %s,
                    revision = revision + 1,
                    updated_at = now()
                WHERE runtime_key = %s AND revision = %s
                RETURNING revision
                """,
                (
                    state.cash,
                    state.units,
                    state.last_price,
                    state.peak_equity,
                    state.day_start_equity,
                    state.last_processed,
                    state.processed_bars,
                    state.last_learning_cycle_bar,
                    runtime_key,
                    commit.expected_revision,
                ),
            )
            if cursor.fetchone() is None:
                raise RuntimeError("runtime revision changed during commit")

            cursor.execute(
                """
                INSERT INTO paper_burnin_snapshots (
                    runtime_key,
                    processed_bars,
                    timestamp_utc,
                    equity
                )
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (runtime_key, processed_bars) DO NOTHING
                """,
                (
                    runtime_key,
                    state.processed_bars,
                    str(state.last_processed or audit["timestamp_utc"]),
                    state.cash + state.units * state.last_price,
                ),
            )

        return CommitOutcome.COMMITTED

    def list_trades(
        self,
        runtime_key: str | None = None,
        *,
        limit: int | None = None,
    ) -> tuple[TradeSnapshot, ...]:
        where = "WHERE runtime_key = %s" if runtime_key is not None else ""
        params: list[object] = [] if runtime_key is None else [runtime_key]
        order = "ORDER BY id ASC"
        if limit is not None:
            order = "ORDER BY id DESC LIMIT %s"
            params.append(limit)

        query = f"""
            SELECT timestamp_utc, symbol, side, quantity, price, status,
                   pnl, confidence, strategy
            FROM paper_trades
            {where}
            {order}
        """
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute(query, params)
            rows = cursor.fetchall()

        if limit is not None:
            rows.reverse()
        return tuple(
            TradeSnapshot(
                timestamp_utc=str(row["timestamp_utc"]),
                symbol=str(row["symbol"]),
                side=str(row["side"]),
                quantity=float(row["quantity"]),
                price=float(row["price"]),
                status=str(row["status"]),
                pnl=float(row["pnl"]),
                confidence=(
                    None if row["confidence"] is None else float(row["confidence"])
                ),
                strategy=str(row["strategy"]),
            )
            for row in rows
        )

    def load_trade_performance(self, runtime_key: str) -> TradePerformanceMetrics:
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    trade_count,
                    realized_pnl,
                    gross_profit,
                    gross_loss,
                    max_drawdown
                FROM paper_trade_performance
                WHERE runtime_key = %s
                """,
                (runtime_key,),
            )
            row = cursor.fetchone()
        if row is None:
            return performance_metrics_from_totals(
                trade_count=0,
                realized_pnl=0.0,
                gross_profit=0.0,
                gross_loss=0.0,
                max_drawdown=0.0,
            )
        return performance_metrics_from_totals(
            trade_count=int(row["trade_count"]),
            realized_pnl=float(row["realized_pnl"]),
            gross_profit=float(row["gross_profit"]),
            gross_loss=float(row["gross_loss"]),
            max_drawdown=float(row["max_drawdown"]),
        )

    def list_burnin_snapshots(self, runtime_key: str) -> tuple[BurnInSnapshot, ...]:
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    timestamp_utc,
                    equity,
                    scheduler_errors,
                    regimes_covered,
                    bootstrap_probability_positive,
                    processed_bars
                FROM paper_burnin_snapshots
                WHERE runtime_key = %s
                ORDER BY processed_bars ASC
                """,
                (runtime_key,),
            )
            rows = cursor.fetchall()
        return tuple(
            BurnInSnapshot(
                timestamp_utc=str(row["timestamp_utc"]),
                equity=float(row["equity"]),
                scheduler_errors=int(row["scheduler_errors"]),
                regimes_covered=int(row["regimes_covered"]),
                bootstrap_probability_positive=float(
                    row["bootstrap_probability_positive"]
                ),
                processed_bars=int(row["processed_bars"]),
            )
            for row in rows
        )

    def save_runtime_status(self, runtime_key: str, status: HostedRuntimeStatus) -> None:
        payload = asdict(status)
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO paper_runtime_status (
                    runtime_key, engine_status, symbol, interval, updated_at_utc, payload
                )
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (runtime_key) DO UPDATE SET
                    engine_status = EXCLUDED.engine_status,
                    symbol = EXCLUDED.symbol,
                    interval = EXCLUDED.interval,
                    updated_at_utc = EXCLUDED.updated_at_utc,
                    payload = EXCLUDED.payload
                """,
                (
                    runtime_key,
                    status.engine_status,
                    status.symbol,
                    status.interval,
                    status.updated_at_utc,
                    Jsonb(payload),
                ),
            )

    def load_runtime_status(self, runtime_key: str) -> HostedRuntimeStatus | None:
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                "SELECT payload FROM paper_runtime_status WHERE runtime_key = %s",
                (runtime_key,),
            )
            row = cursor.fetchone()
        if row is None:
            return None
        payload = row["payload"]
        if not isinstance(payload, dict):
            payload = json.loads(payload)
        return HostedRuntimeStatus(**payload)

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from ai_trading.audit import AuditLog
from ai_trading.config import RiskConfig
from ai_trading.risk import RiskDecision
from ai_trading.runtime import PaperAutonomousRuntime
from ai_trading.runtime_state import RuntimeStateStore
from ai_trading.trade_journal import TradeJournal


def sample_market(n: int = 105) -> pd.DataFrame:
    idx = pd.date_range("2025-01-01", periods=n, freq="5min")
    t = np.arange(n, dtype=float)
    close = 100.0 + 0.1 * t + 2.0 * np.sin(t / 5.0)
    open_ = close * (1.0 + 0.001 * np.sin(t / 3.0))
    return pd.DataFrame(
        {
            "Open": open_,
            "High": np.maximum(open_, close) * 1.005,
            "Low": np.minimum(open_, close) * 0.995,
            "Close": close,
            "Volume": 1000.0 + t,
        },
        index=idx,
    )


def build_file_runtime(tmp_path: Path) -> PaperAutonomousRuntime:
    return PaperAutonomousRuntime(
        risk_config=RiskConfig(min_confidence=0.0),
        state_store=RuntimeStateStore(tmp_path / "state.json"),
        audit_log=AuditLog(tmp_path / "audit.jsonl"),
        online_model_path=tmp_path / "online.joblib",
        lock_path=tmp_path / "runtime.lock",
        symbol="GC=F",
    )


def test_step_at_processes_requested_execution_bar(tmp_path: Path) -> None:
    df = sample_market()
    runtime = build_file_runtime(tmp_path)
    target = runtime._eligible_execution_indices(df)[-3]

    result = runtime.step_at(df, target)

    assert result.processed is True
    assert result.timestamp == str(target)


def test_step_at_is_idempotent_for_same_execution_bar(tmp_path: Path) -> None:
    df = sample_market()
    runtime = build_file_runtime(tmp_path)
    target = runtime._eligible_execution_indices(df)[-2]

    first = runtime.step_at(df, target)
    second = runtime.step_at(df, target)

    assert first.processed is True
    assert second.processed is False
    assert second.reason == "bar already processed"


def test_step_at_rejects_non_eligible_execution_bar(tmp_path: Path) -> None:
    df = sample_market()
    runtime = build_file_runtime(tmp_path)

    with pytest.raises(ValueError, match="eligible execution bar"):
        runtime.step_at(df, df.index[0])


def test_step_at_cannot_regress_to_older_execution_bar(tmp_path: Path) -> None:
    df = sample_market()
    runtime = build_file_runtime(tmp_path)
    eligible = runtime._eligible_execution_indices(df)
    older = eligible[-4]
    newer = eligible[-2]

    first = runtime.step_at(df, newer)
    second = runtime.step_at(df, older)
    state = runtime.state_store.load(runtime.risk_config.starting_cash)

    assert first.processed is True
    assert second.processed is False
    assert second.reason == "bar already processed"
    assert state.last_processed == str(newer)
    assert state.processed_bars == 1


@pytest.mark.parametrize("entry_side", [-1, 1])
def test_hard_risk_stop_liquidates_existing_paper_position_once(
    tmp_path: Path, monkeypatch, entry_side: int
) -> None:
    """A rejected risk stop must not leave a previously opened position exposed."""
    journal = TradeJournal(tmp_path / "trades.jsonl")
    runtime = PaperAutonomousRuntime(
        risk_config=RiskConfig(min_confidence=0.0),
        state_store=RuntimeStateStore(tmp_path / "state.json"),
        trade_journal=journal,
        audit_log=AuditLog(tmp_path / "audit.jsonl"),
        online_model_path=tmp_path / "online.joblib",
        lock_path=tmp_path / "runtime.lock",
        symbol="GC=F",
    )
    decisions = iter((
        RiskDecision(True, entry_side, 10_000.0, "approved"),
        RiskDecision(False, 0, 0.0, "max drawdown reached", liquidate_existing=True),
        RiskDecision(False, 0, 0.0, "max drawdown reached", liquidate_existing=True),
    ))
    monkeypatch.setattr(runtime.risk, "evaluate", lambda prediction, snapshot: next(decisions))
    df = sample_market()
    eligible = runtime._eligible_execution_indices(df)

    opened = runtime.step_at(df, eligible[-4])
    assert opened.processed and opened.approved
    assert runtime.state_store.load(100_000.0).units * entry_side > 0

    stopped = runtime.step_at(df, eligible[-3])
    assert stopped.processed and not stopped.approved
    assert stopped.reason == "max drawdown reached"
    assert runtime.state_store.load(100_000.0).units == 0.0

    still_stopped = runtime.step_at(df, eligible[-2])
    assert still_stopped.processed and not still_stopped.approved
    trades = journal.list()
    assert len(trades) == 2
    assert trades[0].side == ("BUY" if entry_side > 0 else "SELL")
    assert trades[1].side == ("SELL" if entry_side > 0 else "BUY")
    assert trades[1].pnl_known is True
    assert runtime.state_store.load(100_000.0).units == 0.0

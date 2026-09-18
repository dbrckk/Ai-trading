from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from ai_trading.config import RiskConfig
from ai_trading.model_codec import deserialize_model, serialize_model
from ai_trading.online import RiverDirectionModel
from ai_trading.persistence import CommitOutcome, PersistedRuntime, RuntimeStepCommit
from ai_trading.runtime import PaperAutonomousRuntime
from ai_trading.runtime_state import RuntimeState
from ai_trading.runtime_status import HostedRuntimeStatus
from ai_trading.trade_journal import TradeSnapshot

RUNTIME_KEY = "paper:GC=F:5m:online-river:v1"


def sample_market(n: int = 100) -> pd.DataFrame:
    idx = pd.date_range("2025-01-01", periods=n, freq="D")
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


class RecordingPersistence:
    def __init__(
        self,
        loaded: PersistedRuntime,
        *,
        outcome: CommitOutcome = CommitOutcome.COMMITTED,
    ) -> None:
        self.loaded = loaded
        self.outcome = outcome
        self.load_calls: list[tuple[str, float]] = []
        self.commits: list[tuple[str, RuntimeStepCommit]] = []

    def initialize_schema(self) -> None:
        return None

    def load_runtime(self, runtime_key: str, starting_cash: float) -> PersistedRuntime:
        self.load_calls.append((runtime_key, starting_cash))
        return self.loaded

    def commit_step(self, runtime_key: str, commit: RuntimeStepCommit) -> CommitOutcome:
        self.commits.append((runtime_key, commit))
        return self.outcome

    def list_trades(
        self,
        runtime_key: str | None = None,
        *,
        limit: int | None = None,
    ) -> tuple[TradeSnapshot, ...]:
        del runtime_key, limit
        return ()

    def save_runtime_status(self, runtime_key: str, status: HostedRuntimeStatus) -> None:
        del runtime_key, status

    def load_runtime_status(self, runtime_key: str) -> HostedRuntimeStatus | None:
        del runtime_key
        return None


def _persisted_runtime(*, with_model: bool = True) -> PersistedRuntime:
    state = RuntimeState(
        cash=100_000.0,
        units=0.0,
        last_price=100.0,
        peak_equity=100_000.0,
        day_start_equity=100_000.0,
        processed_bars=3,
        last_learning_cycle_bar=0,
    )
    model = serialize_model(RiverDirectionModel()) if with_model else None
    return PersistedRuntime(state=state, model=model, revision=11, is_new=False)


def test_runtime_commits_one_durable_step() -> None:
    persistence = RecordingPersistence(_persisted_runtime())
    runtime = PaperAutonomousRuntime(
        risk_config=RiskConfig(min_confidence=0.0),
        persistence=persistence,
        runtime_key=RUNTIME_KEY,
        symbol="GC=F",
    )

    result = runtime.step(sample_market())

    assert result.processed is True
    assert persistence.load_calls == [(RUNTIME_KEY, 100_000.0)]
    assert len(persistence.commits) == 1
    key, commit = persistence.commits[0]
    assert key == RUNTIME_KEY
    assert commit.expected_revision == 11
    assert commit.state.processed_bars == 4
    assert commit.audit_event == "runtime_step"
    assert commit.audit_payload["processed_bars"] == 4
    assert commit.observed_regime in {
        "bull_high_vol",
        "bull_normal_vol",
        "bear_high_vol",
        "bear_normal_vol",
        "sideways_high_vol",
        "sideways_normal_vol",
    }
    assert commit.audit_payload["observed_regime"] == commit.observed_regime
    assert isinstance(deserialize_model(commit.model), RiverDirectionModel)


def test_runtime_returns_safe_skip_on_revision_conflict() -> None:
    persistence = RecordingPersistence(
        _persisted_runtime(),
        outcome=CommitOutcome.CONFLICT,
    )
    runtime = PaperAutonomousRuntime(
        risk_config=RiskConfig(min_confidence=0.0),
        persistence=persistence,
        runtime_key=RUNTIME_KEY,
        symbol="GC=F",
    )

    result = runtime.step(sample_market())

    assert result.processed is False
    assert result.reason == "persistence revision conflict"
    assert result.processed_bars == 3
    assert len(persistence.commits) == 1


def test_runtime_rejects_missing_model_for_existing_state() -> None:
    persistence = RecordingPersistence(_persisted_runtime(with_model=False))
    runtime = PaperAutonomousRuntime(
        persistence=persistence,
        runtime_key=RUNTIME_KEY,
    )

    with pytest.raises(ValueError, match="missing its online model"):
        runtime.step(sample_market())

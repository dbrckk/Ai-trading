import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

import ai_trading.paper_cycle as paper_cycle_module
import ai_trading.runtime as runtime_module
from ai_trading.config import RiskConfig
from ai_trading.file_persistence import FilePaperPersistence
from ai_trading.model import Prediction
from ai_trading.mtf_shadow_challenger import MultiTimeframeShadowResult
from ai_trading.paper_cycle import PaperCycleRunner
from ai_trading.persistence import build_runtime_key
from ai_trading.runtime import PaperAutonomousRuntime, RuntimeStepResult
from ai_trading.runtime_state import RuntimeState
from ai_trading.shadow_challenger import ShadowChallengerResult


def sample_market(n: int = 110) -> pd.DataFrame:
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


def runtime_factory(tmp_path: Path):
    def build(**kwargs) -> PaperAutonomousRuntime:
        return PaperAutonomousRuntime(
            risk_config=RiskConfig(min_confidence=0.0),
            lock_path=tmp_path / "runtime.lock",
            **kwargs,
        )

    return build


def build_runner(
    tmp_path: Path,
    backend: FilePaperPersistence,
    df: pd.DataFrame,
    *,
    factory=None,
) -> PaperCycleRunner:
    return PaperCycleRunner(
        persistence=backend,
        data_loader=lambda symbol, period, interval: df,
        runtime_factory=factory or runtime_factory(tmp_path),
    )


def build_runtime(
    tmp_path: Path,
    backend: FilePaperPersistence,
    df: pd.DataFrame,
) -> tuple[PaperAutonomousRuntime, tuple[object, ...]]:
    runtime = runtime_factory(tmp_path)(
        symbol="GC=F",
        persistence=backend,
        runtime_key=build_runtime_key("GC=F", "5m"),
    )
    return runtime, runtime._eligible_execution_indices(df)


def test_fresh_runtime_processes_only_latest_eligible_bar(tmp_path: Path) -> None:
    backend = FilePaperPersistence(tmp_path)
    df = sample_market()
    runtime, eligible = build_runtime(tmp_path, backend, df)
    runner = build_runner(tmp_path, backend, df)

    result = runner.run_once(
        symbol="GC=F",
        period="5d",
        interval="5m",
        max_catchup_bars=12,
    )
    state = backend.load_runtime(runtime.runtime_key, 100_000.0).state

    assert result.processed == 1
    assert result.remaining_backlog is False
    assert result.last_processed == str(eligible[-1])
    assert state.last_processed == str(eligible[-1])
    assert state.processed_bars == 1


def test_existing_runtime_catches_up_oldest_first(tmp_path: Path) -> None:
    backend = FilePaperPersistence(tmp_path)
    df = sample_market()
    runtime, eligible = build_runtime(tmp_path, backend, df)
    assert runtime.step_at(df, eligible[-5]).processed is True
    runner = build_runner(tmp_path, backend, df)

    result = runner.run_once(
        symbol="GC=F",
        period="5d",
        interval="5m",
        max_catchup_bars=12,
    )
    audit_rows = [
        json.loads(line)
        for line in backend.audit_log.path.read_text(encoding="utf-8").splitlines()
    ]
    catchup_times = [row["payload"]["execution_time"] for row in audit_rows[1:]]

    assert catchup_times == [str(value) for value in eligible[-4:]]
    assert result.processed == 4
    assert result.remaining_backlog is False
    assert result.last_processed == str(eligible[-1])
    assert result.processed_bars == 5


def test_catchup_cap_leaves_remaining_backlog(tmp_path: Path) -> None:
    backend = FilePaperPersistence(tmp_path)
    df = sample_market()
    runtime, eligible = build_runtime(tmp_path, backend, df)
    assert runtime.step_at(df, eligible[-6]).processed is True
    runner = build_runner(tmp_path, backend, df)

    result = runner.run_once(
        symbol="GC=F",
        period="5d",
        interval="5m",
        max_catchup_bars=2,
    )

    assert result.processed == 2
    assert result.remaining_backlog is True
    assert result.last_processed == str(eligible[-4])
    assert result.processed_bars == 3


def test_catchup_prepares_features_and_labels_once(
    tmp_path: Path,
    monkeypatch,
) -> None:
    backend = FilePaperPersistence(tmp_path)
    df = sample_market()
    runtime, eligible = build_runtime(tmp_path, backend, df)
    assert runtime.step_at(df, eligible[-6]).processed is True

    calls = {"features": 0, "labels": 0}
    original_make_features = runtime_module.make_features
    original_make_labels = runtime_module.make_labels

    def counted_make_features(market):
        calls["features"] += 1
        return original_make_features(market)

    def counted_make_labels(market, *, horizon_bars, return_threshold):
        calls["labels"] += 1
        return original_make_labels(
            market,
            horizon_bars=horizon_bars,
            return_threshold=return_threshold,
        )

    monkeypatch.setattr(runtime_module, "make_features", counted_make_features)
    monkeypatch.setattr(runtime_module, "make_labels", counted_make_labels)

    runner = build_runner(tmp_path, backend, df)
    result = runner.run_once(
        symbol="GC=F",
        period="5d",
        interval="5m",
        max_catchup_bars=12,
    )

    assert result.processed == 5
    assert result.remaining_backlog is False
    assert calls == {"features": 1, "labels": 1}


def test_missing_last_processed_in_history_fails_closed(tmp_path: Path) -> None:
    backend = FilePaperPersistence(tmp_path)
    backend.state_store.save(
        RuntimeState(
            cash=100_000.0,
            units=0.0,
            last_price=0.0,
            peak_equity=100_000.0,
            day_start_equity=100_000.0,
            last_processed="2020-01-01 00:00:00",
            processed_bars=1,
            last_learning_cycle_bar=0,
        )
    )
    runner = build_runner(tmp_path, backend, sample_market())

    with pytest.raises(
        RuntimeError,
        match="persisted last_processed is outside loaded history",
    ):
        runner.run_once(
            symbol="GC=F",
            period="5d",
            interval="5m",
            max_catchup_bars=12,
        )


def test_no_new_bar_is_healthy_and_idempotent(tmp_path: Path) -> None:
    backend = FilePaperPersistence(tmp_path)
    df = sample_market()
    runtime, eligible = build_runtime(tmp_path, backend, df)
    assert runtime.step_at(df, eligible[-1]).processed is True
    runner = build_runner(tmp_path, backend, df)

    result = runner.run_once(
        symbol="GC=F",
        period="5d",
        interval="5m",
        max_catchup_bars=12,
    )

    assert result.processed == 0
    assert result.remaining_backlog is False
    assert result.reason == "no new eligible bar"
    assert result.last_processed == str(eligible[-1])
    assert result.processed_bars == 1


def test_max_catchup_bars_must_be_positive(tmp_path: Path) -> None:
    backend = FilePaperPersistence(tmp_path)
    runner = build_runner(tmp_path, backend, sample_market())

    with pytest.raises(ValueError, match="max_catchup_bars"):
        runner.run_once(
            symbol="GC=F",
            period="5d",
            interval="5m",
            max_catchup_bars=0,
        )


def test_revision_conflict_reloads_and_continues(tmp_path: Path) -> None:
    backend = FilePaperPersistence(tmp_path)
    df = sample_market()
    seed_runtime, eligible = build_runtime(tmp_path, backend, df)
    assert seed_runtime.step_at(df, eligible[-4]).processed is True

    primary = runtime_factory(tmp_path)(
        symbol="GC=F",
        persistence=backend,
        runtime_key=build_runtime_key("GC=F", "5m"),
    )
    competitor = runtime_factory(tmp_path)(
        symbol="GC=F",
        persistence=backend,
        runtime_key=build_runtime_key("GC=F", "5m"),
    )
    conflict_target: list[object] = []

    class ConflictOnceRuntime:
        risk_config = primary.risk_config

        def prepare_market(self, market):
            return primary.prepare_market(market)

        def step_prepared(self, prepared, target):
            if not conflict_target:
                conflict_target.append(target)
                assert competitor.step_prepared(prepared, target).processed is True
                state = backend.load_runtime(primary.runtime_key, 100_000.0).state
                return RuntimeStepResult(
                    processed=False,
                    timestamp=str(target),
                    side=0,
                    confidence=0.0,
                    approved=False,
                    reason="persistence revision conflict",
                    equity=state.cash + state.units * state.last_price,
                    units=state.units,
                    processed_bars=state.processed_bars,
                    retrain_due=False,
                )
            return primary.step_prepared(prepared, target)

    runner = build_runner(
        tmp_path,
        backend,
        df,
        factory=lambda **kwargs: ConflictOnceRuntime(),
    )

    result = runner.run_once(
        symbol="GC=F",
        period="5d",
        interval="5m",
        max_catchup_bars=3,
    )
    final = backend.load_runtime(primary.runtime_key, 100_000.0).state

    assert conflict_target == [eligible[-3]]
    assert final.last_processed == str(eligible[-1])
    assert final.processed_bars == 4
    assert result.processed == 2
    assert result.remaining_backlog is False



def test_shadow_challenger_is_recorded_without_controlling_execution(
    tmp_path: Path,
    monkeypatch,
) -> None:
    backend = FilePaperPersistence(tmp_path)
    df = sample_market()
    runtime, eligible = build_runtime(tmp_path, backend, df)
    target = eligible[-1]
    signal = df.index[int(df.index.get_loc(target)) - 1]
    train_end = df.index[int(df.index.get_loc(signal)) - 1]
    calls: list[object] = []

    def fake_shadow(
        market,
        features,
        labels,
        execution_idx,
        *,
        horizon_bars,
    ):
        del market, features, labels, horizon_bars
        calls.append(execution_idx)
        return ShadowChallengerResult(
            prediction=Prediction(
                side=-1,
                confidence=0.99,
                probabilities={-1: 0.99, 0: 0.005, 1: 0.005},
            ),
            regime="sideways_normal_vol",
            signal_time=str(signal),
            execution_time=str(execution_idx),
            training_rows=120,
            training_end=str(train_end),
            realized_label=-1,
        )

    monkeypatch.setattr(
        paper_cycle_module,
        "evaluate_shadow_challenger",
        fake_shadow,
    )
    monkeypatch.setattr(
        runtime_module.RiverDirectionModel,
        "predict_one",
        lambda self, row: Prediction(
            side=1,
            confidence=0.90,
            probabilities={-1: 0.05, 0: 0.05, 1: 0.90},
        ),
    )

    runner = build_runner(tmp_path, backend, df)
    result = runner.run_once(
        symbol="GC=F",
        period="5d",
        interval="5m",
        max_catchup_bars=12,
        shadow_challenger_enabled=True,
    )

    audit_rows = [
        json.loads(line)
        for line in backend.audit_log.path.read_text(encoding="utf-8").splitlines()
    ]
    payload = audit_rows[-1]["payload"]

    assert result.processed == 1
    assert calls == [target]
    assert payload["prediction"]["side"] == 1
    assert payload["risk_decision"]["side"] == 1
    assert payload["shadow_challenger"]["prediction"]["side"] == -1
    assert payload["shadow_challenger"]["execution_time"] == str(target)
    assert runtime.runtime_key == build_runtime_key("GC=F", "5m")



def test_mtf_shadow_is_audit_only_and_cannot_control_execution(
    tmp_path: Path,
    monkeypatch,
) -> None:
    backend = FilePaperPersistence(tmp_path)
    df = sample_market()
    runtime, eligible = build_runtime(tmp_path, backend, df)
    current_target = eligible[-1]
    mtf_target = eligible[-3]
    mtf_signal = df.index[int(df.index.get_loc(mtf_target)) - 1]

    monkeypatch.setattr(
        paper_cycle_module,
        "evaluate_shadow_challenger",
        lambda *args, **kwargs: None,
    )
    monkeypatch.setattr(
        paper_cycle_module,
        "select_observable_execution_target",
        lambda *args, **kwargs: mtf_target,
    )
    monkeypatch.setattr(
        paper_cycle_module,
        "evaluate_multi_timeframe_shadow",
        lambda *args, **kwargs: MultiTimeframeShadowResult(
            prediction=Prediction(
                side=-1,
                confidence=0.97,
                probabilities={-1: 0.97, 0: 0.02, 1: 0.01},
            ),
            regime="bear_normal_vol",
            signal_time=str(mtf_signal),
            execution_time=str(mtf_target),
            training_rows=500,
            training_end=str(df.index[-20]),
            realized_label=-1,
            horizon_bars=3,
            horizon_minutes=15,
            timeframes=("5m", "15m", "1h", "4h"),
            threshold_at_signal=0.0012,
            minimum_threshold=0.001,
            atr_multiplier=0.25,
            feature_count=29,
        ),
    )
    monkeypatch.setattr(
        runtime_module.RiverDirectionModel,
        "predict_one",
        lambda self, row: Prediction(
            side=1,
            confidence=0.90,
            probabilities={-1: 0.05, 0: 0.05, 1: 0.90},
        ),
    )

    runner = build_runner(tmp_path, backend, df)
    result = runner.run_once(
        symbol="GC=F",
        period="5d",
        interval="5m",
        max_catchup_bars=12,
        shadow_challenger_enabled=True,
    )

    audit_rows = [
        json.loads(line)
        for line in backend.audit_log.path.read_text(encoding="utf-8").splitlines()
    ]
    payload = audit_rows[-1]["payload"]

    assert result.processed == 1
    assert payload["execution_time"] == str(current_target)
    assert payload["prediction"]["side"] == 1
    assert payload["risk_decision"]["side"] == 1
    assert payload["mtf_shadow_challenger"]["prediction"]["side"] == -1
    assert payload["mtf_shadow_challenger"]["execution_time"] == str(mtf_target)
    assert payload["mtf_shadow_challenger"]["horizon_minutes"] == 15

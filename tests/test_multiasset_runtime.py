import json

import joblib
from pathlib import Path

import numpy as np
import pandas as pd

from ai_trading.allocation_state import AllocationStateStore
from ai_trading.audit import AuditLog
from ai_trading.config import RiskConfig
from ai_trading.crisis_state_store import CrisisStateStore
from ai_trading.drift import DistributionDriftReport
from ai_trading.drift_retrain_store import DriftRetrainStore
from ai_trading.economic_meta_store import EconomicMetaStore
from ai_trading.governor_state_store import GovernorStateStore
from ai_trading.lifecycle_log import LifecycleEventLog
from ai_trading.meta_store import MetaRouterStore
from ai_trading.multiasset_runtime import MultiAssetPaperRuntime
from ai_trading.multiasset_state import MultiAssetStateStore
from ai_trading.portfolio import AllocationConfig
from ai_trading.portfolio_risk import PortfolioRiskConfig
from ai_trading.quality_store import QualityStore
from ai_trading.resilience import ResilienceStateStore


def market(seed: int, n: int = 120) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    idx = pd.date_range("2025-01-01", periods=n, freq="D")
    rets = rng.normal(0.0003, 0.01, n)
    close = 100.0 * np.cumprod(1.0 + rets)
    open_ = close * (1.0 + rng.normal(0.0, 0.001, n))
    return pd.DataFrame(
        {
            "Open": open_,
            "High": np.maximum(open_, close) * 1.005,
            "Low": np.minimum(open_, close) * 0.995,
            "Close": close,
            "Volume": 1000.0 + np.arange(n),
        },
        index=idx,
    )


def test_multiasset_runtime_is_persistent_and_idempotent(tmp_path: Path) -> None:
    runtime = MultiAssetPaperRuntime(
        risk_config=RiskConfig(),
        allocation_config=AllocationConfig(max_asset_weight=0.6),
        portfolio_risk_config=PortfolioRiskConfig(
            max_gross_exposure=1.0,
            max_net_exposure=1.0,
            max_asset_exposure=0.6,
            max_pair_correlation=0.99,
        ),
        state_store=MultiAssetStateStore(tmp_path / "state.json"),
        audit_log=AuditLog(tmp_path / "audit.jsonl"),
        lock_path=str(tmp_path / "lock"),
    )
    markets = {"A": market(1), "B": market(2)}

    first = runtime.step(markets)
    second = runtime.step(markets)

    assert first.processed
    assert first.risk_approved
    assert first.equity > 0
    assert sum(abs(v) for v in first.weights.values()) <= 1.0 + 1e-9
    assert not second.processed
    assert "bar already processed" in second.risk_reasons

    records = [
        json.loads(line)
        for line in (tmp_path / "audit.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    step_record = next(record for record in records if record["event"] == "multiasset_runtime_step")
    intelligence = step_record["payload"]["intelligence"]
    assert 0.0 <= intelligence["max_pair_correlation"] <= 1.0
    assert 0.0 < intelligence["correlation_scale"] <= 1.0



def test_failed_drift_retrain_does_not_start_cooldown(
    tmp_path: Path,
    monkeypatch,
) -> None:
    drift_store = DriftRetrainStore(tmp_path / "drift_retrain.json")
    runtime = MultiAssetPaperRuntime(
        risk_config=RiskConfig(),
        allocation_config=AllocationConfig(max_asset_weight=0.6),
        portfolio_risk_config=PortfolioRiskConfig(
            max_gross_exposure=1.0,
            max_net_exposure=1.0,
            max_asset_exposure=0.6,
            max_pair_correlation=0.99,
        ),
        state_store=MultiAssetStateStore(tmp_path / "state.json"),
        audit_log=AuditLog(tmp_path / "audit.jsonl"),
        lock_path=str(tmp_path / "lock"),
        model_root=tmp_path / "online_models",
        batch_model_root=tmp_path / "batch_models",
        specialist_model_root=tmp_path / "specialists",
        drift_retrain_store=drift_store,
    )

    monkeypatch.setattr(
        "ai_trading.multiasset_runtime.detect_distribution_drift",
        lambda *_args, **_kwargs: DistributionDriftReport(
            max_psi=0.8,
            mean_psi=0.4,
            correlation_shift=0.5,
            risk_multiplier=0.25,
            retrain_requested=True,
            drifted_features=("return_1",),
        ),
    )

    def fail_batch_retrain(*_args, **_kwargs):
        raise ValueError("synthetic retrain failure")

    monkeypatch.setattr(runtime, "_load_or_train_batch_model", fail_batch_retrain)

    markets = {"A": market(11, n=180), "B": market(12, n=180)}
    result = runtime.step(markets)

    assert result.processed
    assert drift_store.load() == {}
    assert drift_store.should_retrain("A", processed_bar=1)
    assert drift_store.should_retrain("B", processed_bar=1)



def test_multiasset_runtime_does_not_persist_online_models_before_state_commit(
    tmp_path: Path,
    monkeypatch,
) -> None:
    state_store = MultiAssetStateStore(tmp_path / "state.json")
    runtime = MultiAssetPaperRuntime(
        risk_config=RiskConfig(),
        allocation_config=AllocationConfig(max_asset_weight=0.6),
        portfolio_risk_config=PortfolioRiskConfig(
            max_gross_exposure=1.0,
            max_net_exposure=1.0,
            max_asset_exposure=0.6,
            max_pair_correlation=0.99,
        ),
        state_store=state_store,
        audit_log=AuditLog(tmp_path / "audit.jsonl"),
        lock_path=str(tmp_path / "lock"),
        model_root=tmp_path / "online_models",
        batch_model_root=tmp_path / "batch_models",
        specialist_model_root=tmp_path / "specialists",
    )

    def fail_state_save(_state) -> None:
        raise RuntimeError("synthetic state commit failure")

    monkeypatch.setattr(state_store, "save", fail_state_save)

    with np.testing.assert_raises_regex(RuntimeError, "state commit failure"):
        runtime.step({"A": market(21), "B": market(22)})

    assert not (tmp_path / "online_models" / "A.joblib").exists()
    assert not (tmp_path / "online_models" / "B.joblib").exists()



def test_multiasset_runtime_prefers_checkpoint_over_stale_legacy_state(
    tmp_path: Path,
) -> None:
    state_store = MultiAssetStateStore(tmp_path / "state.json")
    runtime = MultiAssetPaperRuntime(
        risk_config=RiskConfig(),
        allocation_config=AllocationConfig(max_asset_weight=0.6),
        portfolio_risk_config=PortfolioRiskConfig(
            max_gross_exposure=1.0,
            max_net_exposure=1.0,
            max_asset_exposure=0.6,
            max_pair_correlation=0.99,
        ),
        state_store=state_store,
        audit_log=AuditLog(tmp_path / "audit.jsonl"),
        lock_path=str(tmp_path / "lock"),
        model_root=tmp_path / "online_models",
        batch_model_root=tmp_path / "batch_models",
        specialist_model_root=tmp_path / "specialists",
    )
    markets = {"A": market(31), "B": market(32)}

    first = runtime.step(markets)
    assert first.processed
    assert (tmp_path / "multiasset_checkpoint" / "CURRENT").exists()

    legacy = json.loads((tmp_path / "state.json").read_text(encoding="utf-8"))
    legacy["last_processed"] = None
    legacy["processed_bars"] = 0
    (tmp_path / "state.json").write_text(json.dumps(legacy), encoding="utf-8")

    second = runtime.step(markets)

    assert not second.processed
    assert second.risk_reasons == ("bar already processed",)





def test_multiasset_runtime_applies_symbol_specific_execution_costs(
    tmp_path: Path,
    monkeypatch,
) -> None:
    from dataclasses import replace

    from ai_trading.paper_execution import calculate_rebalance_fill as real_fill

    requested_symbols: list[str] = []
    observed_costs: list[tuple[float, float]] = []

    def fake_symbol_config(symbol: str, base: RiskConfig) -> RiskConfig:
        requested_symbols.append(symbol)
        if symbol == "A":
            return replace(base, transaction_cost_bps=1.5, slippage_bps=2.5)
        return replace(base, transaction_cost_bps=7.0, slippage_bps=8.0)

    def capture_fill(**kwargs):
        observed_costs.append(
            (
                float(kwargs["transaction_cost_bps"]),
                float(kwargs["slippage_bps"]),
            )
        )
        return real_fill(**kwargs)

    monkeypatch.setattr(
        "ai_trading.multiasset_runtime.risk_config_for_symbol",
        fake_symbol_config,
    )
    monkeypatch.setattr(
        "ai_trading.multiasset_runtime.calculate_rebalance_fill",
        capture_fill,
    )

    runtime = MultiAssetPaperRuntime(
        risk_config=RiskConfig(),
        allocation_config=AllocationConfig(max_asset_weight=0.6),
        portfolio_risk_config=PortfolioRiskConfig(
            max_gross_exposure=1.0,
            max_net_exposure=1.0,
            max_asset_exposure=0.6,
            max_pair_correlation=0.99,
        ),
        state_store=MultiAssetStateStore(tmp_path / "state.json"),
        audit_log=AuditLog(tmp_path / "audit.jsonl"),
        lock_path=str(tmp_path / "lock"),
        model_root=tmp_path / "online_models",
        batch_model_root=tmp_path / "batch_models",
        specialist_model_root=tmp_path / "specialists",
    )

    result = runtime.step({"A": market(41), "B": market(42)})

    assert result.processed
    assert requested_symbols == ["A", "B"]
    assert observed_costs == [(1.5, 2.5), (7.0, 8.0)]



def test_multiasset_runtime_defers_control_state_until_checkpoint_commit(
    tmp_path: Path,
    monkeypatch,
) -> None:
    allocation_store = AllocationStateStore(tmp_path / "allocation.json")
    crisis_store = CrisisStateStore(tmp_path / "crisis.json")
    resilience_store = ResilienceStateStore(tmp_path / "resilience.json")
    governor_store = GovernorStateStore(tmp_path / "governor.json")

    runtime = MultiAssetPaperRuntime(
        risk_config=RiskConfig(),
        allocation_config=AllocationConfig(max_asset_weight=0.6),
        portfolio_risk_config=PortfolioRiskConfig(
            max_gross_exposure=1.0,
            max_net_exposure=1.0,
            max_asset_exposure=0.6,
            max_pair_correlation=0.99,
        ),
        state_store=MultiAssetStateStore(tmp_path / "state.json"),
        audit_log=AuditLog(tmp_path / "audit.jsonl"),
        lock_path=str(tmp_path / "lock"),
        model_root=tmp_path / "online_models",
        batch_model_root=tmp_path / "batch_models",
        specialist_model_root=tmp_path / "specialists",
        allocation_state_store=allocation_store,
        crisis_state_store=crisis_store,
        resilience_state_store=resilience_store,
        governor_state_store=governor_store,
    )

    def fail_checkpoint(*_args, **_kwargs) -> None:
        raise RuntimeError("synthetic checkpoint failure")

    monkeypatch.setattr(runtime.checkpoint_store, "commit", fail_checkpoint)

    with np.testing.assert_raises_regex(RuntimeError, "checkpoint failure"):
        runtime.step({"A": market(51), "B": market(52)})

    assert not allocation_store.path.exists()
    assert not crisis_store.path.exists()
    assert not resilience_store.path.exists()
    assert not governor_store.path.exists()



def test_multiasset_runtime_defers_learning_side_effects_until_checkpoint_commit(
    tmp_path: Path,
    monkeypatch,
) -> None:
    quality_store = QualityStore(tmp_path / "quality.json")
    meta_store = MetaRouterStore(tmp_path / "meta.json")
    economic_store = EconomicMetaStore(tmp_path / "economic.json")
    lifecycle_log = LifecycleEventLog(tmp_path / "lifecycle.jsonl")
    drift_store = DriftRetrainStore(tmp_path / "drift.json")

    runtime = MultiAssetPaperRuntime(
        risk_config=RiskConfig(),
        allocation_config=AllocationConfig(max_asset_weight=0.6),
        portfolio_risk_config=PortfolioRiskConfig(
            max_gross_exposure=1.0,
            max_net_exposure=1.0,
            max_asset_exposure=0.6,
            max_pair_correlation=0.99,
        ),
        state_store=MultiAssetStateStore(tmp_path / "state.json"),
        audit_log=AuditLog(tmp_path / "audit.jsonl"),
        lock_path=str(tmp_path / "lock"),
        model_root=tmp_path / "online_models",
        batch_model_root=tmp_path / "batch_models",
        specialist_model_root=tmp_path / "specialists",
        quality_store=quality_store,
        meta_store=meta_store,
        economic_meta_store=economic_store,
        lifecycle_log=lifecycle_log,
        drift_retrain_store=drift_store,
    )

    def fail_checkpoint(*_args, **_kwargs) -> None:
        raise RuntimeError("synthetic checkpoint failure")

    monkeypatch.setattr(runtime.checkpoint_store, "commit", fail_checkpoint)

    with np.testing.assert_raises_regex(RuntimeError, "checkpoint failure"):
        runtime.step({"A": market(61), "B": market(62)})

    assert not quality_store.path.exists()
    assert not meta_store.path.exists()
    assert not economic_store.path.exists()
    assert not lifecycle_log.path.exists()
    assert not drift_store.path.exists()



def test_multiasset_model_paths_are_collision_resistant(tmp_path: Path) -> None:
    runtime = MultiAssetPaperRuntime(
        state_store=MultiAssetStateStore(tmp_path / "state.json"),
        audit_log=AuditLog(tmp_path / "audit.jsonl"),
        lock_path=str(tmp_path / "lock"),
        model_root=tmp_path / "online_models",
        batch_model_root=tmp_path / "batch_models",
        specialist_model_root=tmp_path / "specialists",
    )

    symbols = ("GC=F", "GC/F", "^GC_F")

    assert len({runtime._model_path(symbol) for symbol in symbols}) == 3
    assert len({runtime._batch_model_path(symbol) for symbol in symbols}) == 3
    assert len(
        {runtime._specialist_path(symbol, "trend") for symbol in symbols}
    ) == 3


def test_multiasset_online_model_legacy_path_is_migrated(tmp_path: Path) -> None:
    runtime = MultiAssetPaperRuntime(
        state_store=MultiAssetStateStore(tmp_path / "state.json"),
        audit_log=AuditLog(tmp_path / "audit.jsonl"),
        lock_path=str(tmp_path / "lock"),
        model_root=tmp_path / "online_models",
        batch_model_root=tmp_path / "batch_models",
        specialist_model_root=tmp_path / "specialists",
    )
    symbol = "GC=F"
    legacy_path = runtime._legacy_model_path(symbol)
    legacy_path.parent.mkdir(parents=True, exist_ok=True)
    expected = {"legacy": True}
    joblib.dump(expected, legacy_path)

    loaded = runtime._load_model(symbol)

    assert loaded == expected
    assert runtime._model_path(symbol).exists()
    assert joblib.load(runtime._model_path(symbol)) == expected


def test_multiasset_batch_and_specialist_legacy_paths_are_migrated(
    tmp_path: Path,
) -> None:
    runtime = MultiAssetPaperRuntime(
        state_store=MultiAssetStateStore(tmp_path / "state.json"),
        audit_log=AuditLog(tmp_path / "audit.jsonl"),
        lock_path=str(tmp_path / "lock"),
        model_root=tmp_path / "online_models",
        batch_model_root=tmp_path / "batch_models",
        specialist_model_root=tmp_path / "specialists",
    )
    symbol = "GC=F"
    features = pd.DataFrame(index=pd.date_range("2025-01-01", periods=2))
    labels = pd.Series(index=features.index, dtype=float)
    signal_idx = features.index[-1]

    legacy_batch = runtime._legacy_batch_model_path(symbol)
    legacy_batch.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump({"batch": True}, legacy_batch)

    legacy_specialist = runtime._legacy_specialist_path(symbol, "trend")
    legacy_specialist.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump({"specialist": True}, legacy_specialist)

    batch = runtime._load_or_train_batch_model(
        symbol,
        features,
        labels,
        signal_idx,
    )
    specialist = runtime._load_or_train_specialist(
        symbol,
        "trend",
        features,
        labels,
        signal_idx,
    )

    assert batch == {"batch": True}
    assert specialist == {"specialist": True}
    assert runtime._batch_model_path(symbol).exists()
    assert runtime._specialist_path(symbol, "trend").exists()

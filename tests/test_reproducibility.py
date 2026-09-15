import pandas as pd

from ai_trading.benchmark_gate import BenchmarkGateResult
from ai_trading.bootstrap_gate import BootstrapGateResult
from ai_trading.cost_stress_gate import CostStressGateResult
from ai_trading.dataset_evidence import build_dataset_evidence
from ai_trading.quantitative_artifact import build_quantitative_artifact
from ai_trading.quantitative_qualification import QuantitativeQualification
from ai_trading.regime_gate import RegimeGateResult
from ai_trading.reproducibility import verify_quantitative_reproducibility
from ai_trading.sensitivity_gate import SensitivityGateResult


def market() -> pd.DataFrame:
    index = pd.date_range("2025-01-01", periods=4, freq="D")
    return pd.DataFrame(
        {
            "Open": [100.0, 101.0, 102.0, 103.0],
            "High": [101.0, 102.0, 103.0, 104.0],
            "Low": [99.0, 100.0, 101.0, 102.0],
            "Close": [100.5, 101.5, 102.5, 103.5],
            "Volume": [1000.0, 1100.0, 1200.0, 1300.0],
        },
        index=index,
    )


def artifact():
    frame = market()
    dataset = build_dataset_evidence(
        frame,
        provider="yfinance",
        acquired_at_utc="2026-09-15T00:00:00+00:00",
    )
    qualification = QuantitativeQualification(True, 5, 5, ())
    return build_quantitative_artifact(
        symbol="GC=F",
        period="10y",
        interval="1d",
        dataset=dataset,
        config_hash="b" * 64,
        qualification=qualification,
        benchmark=BenchmarkGateResult(True, ()),
        regime=RegimeGateResult(True, 3, "range", -0.02, 0.10, ()),
        bootstrap=BootstrapGateResult(True, ()),
        sensitivity=SensitivityGateResult(True, 6, 6, 1.0, 0.01, 0.5, 0.1, ()),
        cost_stress=CostStressGateResult(True, 3, 3, 1.0, 0.01, 0.5, 0.1, ()),
    )


def test_reproducibility_accepts_exact_inputs() -> None:
    result = verify_quantitative_reproducibility(
        artifact(),
        market(),
        provider="yfinance",
        config_hash="b" * 64,
    )

    assert result.valid
    assert result.reasons == ()


def test_reproducibility_rejects_dataset_tampering() -> None:
    modified = market()
    modified.iloc[2, modified.columns.get_loc("Close")] += 0.01

    result = verify_quantitative_reproducibility(artifact(), modified)

    assert not result.valid
    assert "dataset content hash mismatch" in result.reasons


def test_reproducibility_rejects_provider_change() -> None:
    result = verify_quantitative_reproducibility(
        artifact(),
        market(),
        provider="alternate",
    )

    assert not result.valid
    assert "dataset provider mismatch" in result.reasons


def test_reproducibility_rejects_config_change() -> None:
    result = verify_quantitative_reproducibility(
        artifact(),
        market(),
        config_hash="c" * 64,
    )

    assert not result.valid
    assert "benchmark configuration hash mismatch" in result.reasons

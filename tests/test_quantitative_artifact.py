from ai_trading.benchmark_gate import BenchmarkGateResult
from ai_trading.bootstrap_gate import BootstrapGateResult
from ai_trading.cost_stress_gate import CostStressGateResult
from ai_trading.quantitative_artifact import (
    build_quantitative_artifact,
    quantitative_artifact_hash,
)
from ai_trading.quantitative_qualification import QuantitativeQualification
from ai_trading.regime_gate import RegimeGateResult
from ai_trading.sensitivity_gate import SensitivityGateResult


def test_quantitative_artifact_hash_matches_content() -> None:
    qualification = QuantitativeQualification(True, 5, 5, ())
    artifact = build_quantitative_artifact(
        symbol="GC=F",
        period="10y",
        interval="1d",
        qualification=qualification,
        benchmark=BenchmarkGateResult(True, ()),
        regime=RegimeGateResult(True, 3, "range", -0.02, 0.10, ()),
        bootstrap=BootstrapGateResult(True, ()),
        sensitivity=SensitivityGateResult(True, 6, 6, 1.0, 0.01, 0.5, 0.1, ()),
        cost_stress=CostStressGateResult(True, 3, 3, 1.0, 0.01, 0.5, 0.1, ()),
    )

    assert artifact.verdict == "QUALIFIED"
    assert len(artifact.evidence_hash) == 64
    assert artifact.evidence_hash == quantitative_artifact_hash(artifact)

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path

from .benchmark_gate import BenchmarkGateResult
from .bootstrap_gate import BootstrapGateResult
from .cost_stress_gate import CostStressGateResult
from .quantitative_qualification import QuantitativeQualification
from .regime_gate import RegimeGateResult
from .sensitivity_gate import SensitivityGateResult


@dataclass(frozen=True)
class QuantitativeQualificationArtifact:
    created_at_utc: str
    symbol: str
    period: str
    interval: str
    verdict: str
    passed_gates: int
    total_gates: int
    reasons: tuple[str, ...]
    benchmark: BenchmarkGateResult
    regime: RegimeGateResult
    bootstrap: BootstrapGateResult
    sensitivity: SensitivityGateResult
    cost_stress: CostStressGateResult


def build_quantitative_artifact(
    *,
    symbol: str,
    period: str,
    interval: str,
    qualification: QuantitativeQualification,
    benchmark: BenchmarkGateResult,
    regime: RegimeGateResult,
    bootstrap: BootstrapGateResult,
    sensitivity: SensitivityGateResult,
    cost_stress: CostStressGateResult,
) -> QuantitativeQualificationArtifact:
    return QuantitativeQualificationArtifact(
        created_at_utc=datetime.now(UTC).isoformat(),
        symbol=symbol,
        period=period,
        interval=interval,
        verdict="QUALIFIED" if qualification.qualified else "REJECTED",
        passed_gates=qualification.passed_gates,
        total_gates=qualification.total_gates,
        reasons=qualification.reasons,
        benchmark=benchmark,
        regime=regime,
        bootstrap=bootstrap,
        sensitivity=sensitivity,
        cost_stress=cost_stress,
    )


def save_quantitative_artifact(
    artifact: QuantitativeQualificationArtifact,
    path: str | Path,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    temp = target.with_suffix(".tmp")
    temp.write_text(
        json.dumps(asdict(artifact), sort_keys=True, indent=2),
        encoding="utf-8",
    )
    temp.replace(target)

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path

from .benchmark_gate import BenchmarkGateResult
from .bootstrap_gate import BootstrapGateResult
from .cost_stress_gate import CostStressGateResult
from .dataset_evidence import DatasetEvidence
from .quantitative_qualification import QuantitativeQualification
from .regime_gate import RegimeGateResult
from .sensitivity_gate import SensitivityGateResult


@dataclass(frozen=True)
class QuantitativeQualificationArtifact:
    created_at_utc: str
    symbol: str
    period: str
    interval: str
    dataset: DatasetEvidence
    config_hash: str
    verdict: str
    passed_gates: int
    total_gates: int
    reasons: tuple[str, ...]
    benchmark: BenchmarkGateResult
    regime: RegimeGateResult
    bootstrap: BootstrapGateResult
    sensitivity: SensitivityGateResult
    cost_stress: CostStressGateResult
    evidence_hash: str


def _evidence_payload(artifact: QuantitativeQualificationArtifact) -> dict:
    payload = asdict(artifact)
    payload.pop("evidence_hash", None)
    return payload


def quantitative_artifact_hash(
    artifact: QuantitativeQualificationArtifact,
) -> str:
    canonical = json.dumps(
        _evidence_payload(artifact),
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return sha256(canonical).hexdigest()


def build_quantitative_artifact(
    *,
    symbol: str,
    period: str,
    interval: str,
    dataset: DatasetEvidence,
    config_hash: str,
    qualification: QuantitativeQualification,
    benchmark: BenchmarkGateResult,
    regime: RegimeGateResult,
    bootstrap: BootstrapGateResult,
    sensitivity: SensitivityGateResult,
    cost_stress: CostStressGateResult,
) -> QuantitativeQualificationArtifact:
    artifact = QuantitativeQualificationArtifact(
        created_at_utc=datetime.now(UTC).isoformat(),
        symbol=symbol,
        period=period,
        interval=interval,
        dataset=dataset,
        config_hash=config_hash,
        verdict="QUALIFIED" if qualification.qualified else "REJECTED",
        passed_gates=qualification.passed_gates,
        total_gates=qualification.total_gates,
        reasons=qualification.reasons,
        benchmark=benchmark,
        regime=regime,
        bootstrap=bootstrap,
        sensitivity=sensitivity,
        cost_stress=cost_stress,
        evidence_hash="",
    )
    return QuantitativeQualificationArtifact(
        created_at_utc=artifact.created_at_utc,
        symbol=artifact.symbol,
        period=artifact.period,
        interval=artifact.interval,
        dataset=artifact.dataset,
        config_hash=artifact.config_hash,
        verdict=artifact.verdict,
        passed_gates=artifact.passed_gates,
        total_gates=artifact.total_gates,
        reasons=artifact.reasons,
        benchmark=artifact.benchmark,
        regime=artifact.regime,
        bootstrap=artifact.bootstrap,
        sensitivity=artifact.sensitivity,
        cost_stress=artifact.cost_stress,
        evidence_hash=quantitative_artifact_hash(artifact),
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


def load_quantitative_artifact(
    path: str | Path,
) -> QuantitativeQualificationArtifact | None:
    target = Path(path)
    if not target.exists():
        return None
    try:
        payload = json.loads(target.read_text(encoding="utf-8"))
        artifact = QuantitativeQualificationArtifact(**payload)
    except (json.JSONDecodeError, TypeError):
        return None
    if artifact.evidence_hash != quantitative_artifact_hash(artifact):
        return None
    return artifact

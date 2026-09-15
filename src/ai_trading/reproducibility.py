from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from .dataset_evidence import DatasetEvidence, build_dataset_evidence
from .quantitative_artifact import QuantitativeQualificationArtifact, quantitative_artifact_hash


@dataclass(frozen=True)
class ReproducibilityVerification:
    valid: bool
    reasons: tuple[str, ...]


def verify_quantitative_reproducibility(
    artifact: QuantitativeQualificationArtifact,
    df: pd.DataFrame,
    *,
    provider: str | None = None,
    config_hash: str | None = None,
) -> ReproducibilityVerification:
    """Fail closed when current inputs cannot reproduce artifact identity."""
    failures: list[str] = []

    if artifact.evidence_hash != quantitative_artifact_hash(artifact):
        failures.append("quantitative artifact content hash mismatch")

    expected = artifact.dataset
    current = build_dataset_evidence(
        df,
        provider=provider if provider is not None else expected.provider,
        acquired_at_utc=expected.acquired_at_utc,
    )

    if current.data_hash != expected.data_hash:
        failures.append("dataset content hash mismatch")
    if current.rows != expected.rows:
        failures.append("dataset row count mismatch")
    if current.first_timestamp != expected.first_timestamp:
        failures.append("dataset first timestamp mismatch")
    if current.last_timestamp != expected.last_timestamp:
        failures.append("dataset last timestamp mismatch")
    if current.columns != expected.columns:
        failures.append("dataset columns mismatch")
    if provider is not None and provider != expected.provider:
        failures.append("dataset provider mismatch")
    if config_hash is not None and config_hash != artifact.config_hash:
        failures.append("benchmark configuration hash mismatch")

    return ReproducibilityVerification(not failures, tuple(failures))


def dataset_identity_matches(
    expected: DatasetEvidence,
    df: pd.DataFrame,
) -> bool:
    """Convenience predicate for exact market-data identity."""
    current = build_dataset_evidence(
        df,
        provider=expected.provider,
        acquired_at_utc=expected.acquired_at_utc,
    )
    return current == expected

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from hashlib import sha256
from json import dumps, loads
from pathlib import Path

SCORE_VERSION = "1.0.0"


@dataclass(frozen=True)
class ReadinessComponents:
    performance: float
    robustness: float
    reliability: float
    recovery: float
    data_quality: float
    model_stability: float
    execution_quality: float


@dataclass(frozen=True)
class ReadinessWeights:
    performance: float = 0.20
    robustness: float = 0.15
    reliability: float = 0.20
    recovery: float = 0.10
    data_quality: float = 0.10
    model_stability: float = 0.15
    execution_quality: float = 0.10


@dataclass(frozen=True)
class CompositeReadiness:
    version: str
    score: float
    components: ReadinessComponents
    weights: ReadinessWeights
    passed: bool
    reasons: tuple[str, ...]
    evidence_hash: str


@dataclass(frozen=True)
class ReadinessPolicy:
    min_score: float = 90.0
    min_component: float = 75.0


def _bounded(value: float) -> float:
    return max(0.0, min(100.0, float(value)))


def _evidence_hash(
    version: str,
    components: ReadinessComponents,
    weights: ReadinessWeights,
) -> str:
    payload = {
        "version": version,
        "components": asdict(components),
        "weights": asdict(weights),
    }
    raw = dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return sha256(raw).hexdigest()


def evaluate_composite_readiness(
    components: ReadinessComponents,
    *,
    weights: ReadinessWeights | None = None,
    policy: ReadinessPolicy | None = None,
    version: str = SCORE_VERSION,
) -> CompositeReadiness:
    weights = weights or ReadinessWeights()
    policy = policy or ReadinessPolicy()

    component_values = {
        name: _bounded(value)
        for name, value in asdict(components).items()
    }
    weight_values = asdict(weights)
    total_weight = sum(max(0.0, float(value)) for value in weight_values.values())
    if total_weight <= 0:
        raise ValueError("readiness weights must sum to a positive value")

    weighted = sum(
        component_values[name] * max(0.0, float(weight_values[name]))
        for name in component_values
    )
    score = weighted / total_weight

    reasons: list[str] = []
    for name, value in component_values.items():
        if value < policy.min_component:
            reasons.append(f"{name} below minimum component threshold")
    if score < policy.min_score:
        reasons.append("composite readiness score below threshold")

    normalized = ReadinessComponents(**component_values)
    return CompositeReadiness(
        version=version,
        score=float(score),
        components=normalized,
        weights=weights,
        passed=not reasons,
        reasons=tuple(reasons),
        evidence_hash=_evidence_hash(version, normalized, weights),
    )


@dataclass(frozen=True)
class ReadinessHistoryRecord:
    created_at_utc: str
    result: CompositeReadiness
    prev_hash: str = ""
    record_hash: str = ""


@dataclass(frozen=True)
class ReadinessChainReport:
    valid: bool
    records: int
    legacy_records: int
    reason: str = ""


class ReadinessHistoryStore:
    def __init__(
        self,
        path: str | Path = "artifacts/readiness_history.jsonl",
    ) -> None:
        self.path = Path(path)

    def append(self, result: CompositeReadiness) -> ReadinessHistoryRecord:
        previous = self.list()
        prev_hash = previous[-1].record_hash if previous else ""
        created_at_utc = datetime.now(UTC).isoformat()
        payload = {
            "created_at_utc": created_at_utc,
            "prev_hash": prev_hash,
            "result": {
                **asdict(result),
                "reasons": list(result.reasons),
            },
        }
        canonical = dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        record_hash = sha256(canonical).hexdigest()
        record = ReadinessHistoryRecord(
            created_at_utc=created_at_utc,
            result=result,
            prev_hash=prev_hash,
            record_hash=record_hash,
        )
        payload["record_hash"] = record_hash
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(dumps(payload, sort_keys=True) + "\n")
        return record

    def list(self) -> list[ReadinessHistoryRecord]:
        if not self.path.exists():
            return []
        records: list[ReadinessHistoryRecord] = []
        with self.path.open("r", encoding="utf-8") as handle:
            for line in handle:
                if not line.strip():
                    continue
                payload = loads(line)
                result_payload = payload["result"]
                result = CompositeReadiness(
                    version=result_payload["version"],
                    score=float(result_payload["score"]),
                    components=ReadinessComponents(**result_payload["components"]),
                    weights=ReadinessWeights(**result_payload["weights"]),
                    passed=bool(result_payload["passed"]),
                    reasons=tuple(result_payload.get("reasons", ())),
                    evidence_hash=result_payload["evidence_hash"],
                )
                records.append(
                    ReadinessHistoryRecord(
                        created_at_utc=payload["created_at_utc"],
                        result=result,
                        prev_hash=payload.get("prev_hash", ""),
                        record_hash=payload.get("record_hash", ""),
                    )
                )
        return records


    def verify_chain(self) -> ReadinessChainReport:
        if not self.path.exists():
            return ReadinessChainReport(valid=True, records=0, legacy_records=0)

        previous_hash = ""
        records = 0
        legacy_records = 0
        with self.path.open("r", encoding="utf-8") as handle:
            for line in handle:
                if not line.strip():
                    continue
                records += 1
                try:
                    payload = loads(line)
                except Exception:
                    return ReadinessChainReport(
                        valid=False,
                        records=records,
                        legacy_records=legacy_records,
                        reason="invalid readiness history JSON",
                    )

                record_hash = payload.get("record_hash", "")
                prev_hash = payload.get("prev_hash", "")
                if not record_hash:
                    legacy_records += 1
                    previous_hash = ""
                    continue

                if prev_hash != previous_hash:
                    return ReadinessChainReport(
                        valid=False,
                        records=records,
                        legacy_records=legacy_records,
                        reason="readiness history previous hash mismatch",
                    )

                canonical_payload = dict(payload)
                canonical_payload.pop("record_hash", None)
                canonical = dumps(
                    canonical_payload,
                    sort_keys=True,
                    separators=(",", ":"),
                ).encode("utf-8")
                expected = sha256(canonical).hexdigest()
                if record_hash != expected:
                    return ReadinessChainReport(
                        valid=False,
                        records=records,
                        legacy_records=legacy_records,
                        reason="readiness history record hash mismatch",
                    )
                previous_hash = record_hash

        return ReadinessChainReport(
            valid=True,
            records=records,
            legacy_records=legacy_records,
        )

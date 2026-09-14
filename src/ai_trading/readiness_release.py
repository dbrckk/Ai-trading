from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from hashlib import sha256
from hmac import compare_digest, new as hmac_new
from json import JSONDecodeError, dumps, loads
from pathlib import Path

from .governor_state_store import GovernorState
from .qualification_store import QualificationRecord
from .readiness_score import CompositeReadiness, ReadinessChainReport
from .readiness_trend import ReadinessTrend
from .resilience import ResilienceState

RELEASE_FORMAT_VERSION = "1.0.0"


@dataclass(frozen=True)
class ReadinessRelease:
    format_version: str
    created_at_utc: str
    composite_version: str
    composite_score: float
    composite_evidence_hash: str
    readiness_chain_head: str
    readiness_chain_records: int
    qualification_hash: str
    governor_hash: str
    resilience_hash: str
    trend_status: str
    trend_observations: int
    trend_score_change: float
    release_hash: str
    signature_algorithm: str
    signature: str


@dataclass(frozen=True)
class ReadinessReleaseVerification:
    valid: bool
    reason: str = ""


def _canonical_hash(payload: object) -> str:
    raw = dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return sha256(raw).hexdigest()


def _release_payload(
    *,
    created_at_utc: str,
    composite: CompositeReadiness,
    chain_head: str,
    chain: ReadinessChainReport,
    qualification: QualificationRecord,
    governor: GovernorState,
    resilience: ResilienceState,
    trend: ReadinessTrend,
) -> dict[str, object]:
    return {
        "format_version": RELEASE_FORMAT_VERSION,
        "created_at_utc": created_at_utc,
        "composite_version": composite.version,
        "composite_score": composite.score,
        "composite_evidence_hash": composite.evidence_hash,
        "readiness_chain_head": chain_head,
        "readiness_chain_records": chain.records,
        "qualification_hash": _canonical_hash(asdict(qualification)),
        "governor_hash": _canonical_hash(asdict(governor)),
        "resilience_hash": _canonical_hash(asdict(resilience)),
        "trend_status": trend.status,
        "trend_observations": trend.observations,
        "trend_score_change": trend.score_change,
    }


def create_readiness_release(
    *,
    composite: CompositeReadiness,
    chain_head: str,
    chain: ReadinessChainReport,
    qualification: QualificationRecord,
    governor: GovernorState,
    resilience: ResilienceState,
    trend: ReadinessTrend,
    created_at_utc: str | None = None,
    signing_key: str | bytes | None = None,
) -> ReadinessRelease:
    if not chain.valid:
        raise ValueError("cannot release from invalid readiness history chain")
    if not chain_head:
        raise ValueError("cannot release without readiness chain head")
    if not composite.passed:
        raise ValueError("cannot release failing composite readiness")
    if trend.status != "stable":
        raise ValueError("cannot release unstable readiness trend")

    created_at_utc = created_at_utc or datetime.now(UTC).isoformat()
    payload = _release_payload(
        created_at_utc=created_at_utc,
        composite=composite,
        chain_head=chain_head,
        chain=chain,
        qualification=qualification,
        governor=governor,
        resilience=resilience,
        trend=trend,
    )
    release_hash = _canonical_hash(payload)
    signature_algorithm = "HMAC-SHA256" if signing_key is not None else "NONE"
    signature = ""
    if signing_key is not None:
        key = signing_key.encode("utf-8") if isinstance(signing_key, str) else signing_key
        signature = hmac_new(
            key,
            release_hash.encode("utf-8"),
            sha256,
        ).hexdigest()
    return ReadinessRelease(
        **payload,
        release_hash=release_hash,
        signature_algorithm=signature_algorithm,
        signature=signature,
    )


def verify_readiness_release(
    release: ReadinessRelease,
    *,
    composite: CompositeReadiness,
    chain_head: str,
    chain: ReadinessChainReport,
    qualification: QualificationRecord,
    governor: GovernorState,
    resilience: ResilienceState,
    trend: ReadinessTrend,
    signing_key: str | bytes | None = None,
    require_signature: bool = True,
) -> ReadinessReleaseVerification:
    if release.format_version != RELEASE_FORMAT_VERSION:
        return ReadinessReleaseVerification(False, "unsupported readiness release format")
    if not chain.valid:
        return ReadinessReleaseVerification(False, "readiness chain is invalid")
    if release.readiness_chain_head != chain_head:
        return ReadinessReleaseVerification(False, "readiness chain head changed")
    if release.readiness_chain_records != chain.records:
        return ReadinessReleaseVerification(False, "readiness chain length changed")

    payload = _release_payload(
        created_at_utc=release.created_at_utc,
        composite=composite,
        chain_head=chain_head,
        chain=chain,
        qualification=qualification,
        governor=governor,
        resilience=resilience,
        trend=trend,
    )
    expected = _canonical_hash(payload)
    if release.release_hash != expected:
        return ReadinessReleaseVerification(False, "readiness release hash mismatch")

    if require_signature:
        if release.signature_algorithm != "HMAC-SHA256" or not release.signature:
            return ReadinessReleaseVerification(False, "readiness release signature missing")
        if signing_key is None:
            return ReadinessReleaseVerification(False, "readiness release signing key missing")
        key = signing_key.encode("utf-8") if isinstance(signing_key, str) else signing_key
        expected_signature = hmac_new(
            key,
            release.release_hash.encode("utf-8"),
            sha256,
        ).hexdigest()
        if not compare_digest(release.signature, expected_signature):
            return ReadinessReleaseVerification(False, "readiness release signature invalid")

    return ReadinessReleaseVerification(True)


class ReadinessReleaseStore:
    def __init__(
        self,
        path: str | Path = "artifacts/readiness_release.json",
    ) -> None:
        self.path = Path(path)

    def save(self, release: ReadinessRelease) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temp = self.path.with_suffix(".tmp")
        temp.write_text(dumps(asdict(release), sort_keys=True), encoding="utf-8")
        temp.replace(self.path)

    def load(self) -> ReadinessRelease | None:
        if not self.path.exists():
            return None
        try:
            payload = loads(self.path.read_text(encoding="utf-8"))
        except JSONDecodeError:
            return None
        return ReadinessRelease(**payload)

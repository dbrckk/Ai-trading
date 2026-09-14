from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path

from .reliability import ReliabilityReport
from .soak import SoakResult
from .soak_gate import SoakQualification


@dataclass(frozen=True)
class QualificationRecord:
    created_at_utc: str
    passed: bool
    success_ratio: float
    reasons: tuple[str, ...]
    cycles: int
    failures: int
    max_drawdown: float
    governor_verdict: str
    crisis_mode: str
    symbols: tuple[str, ...] = ()
    period: str = ""
    interval: str = ""
    reliability_score: float | None = None
    normal_ratio: float | None = None
    halt_ratio: float | None = None
    mttr_seconds: float | None = None
    mtbf_seconds: float | None = None


class QualificationStore:
    def __init__(
        self,
        path: str | Path = "artifacts/soak/qualification.json",
    ) -> None:
        self.path = Path(path)

    def load(self) -> QualificationRecord | None:
        if not self.path.exists():
            return None
        payload = json.loads(self.path.read_text(encoding="utf-8"))
        payload["reasons"] = tuple(payload.get("reasons", ()))
        payload["symbols"] = tuple(payload.get("symbols", ()))
        return QualificationRecord(**payload)

    def save(
        self,
        result: SoakResult,
        qualification: SoakQualification,
        *,
        symbols: tuple[str, ...] = (),
        period: str = "",
        interval: str = "",
        reliability: ReliabilityReport | None = None,
    ) -> QualificationRecord:
        record = QualificationRecord(
            created_at_utc=datetime.now(UTC).isoformat(),
            passed=qualification.passed,
            success_ratio=qualification.success_ratio,
            reasons=qualification.reasons,
            cycles=result.cycles,
            failures=result.failures,
            max_drawdown=result.max_drawdown,
            governor_verdict=result.governor_verdict,
            crisis_mode=result.crisis_mode,
            symbols=tuple(symbols),
            period=period,
            interval=interval,
            reliability_score=(
                reliability.reliability_score if reliability is not None else None
            ),
            normal_ratio=(reliability.normal_ratio if reliability is not None else None),
            halt_ratio=(reliability.halt_ratio if reliability is not None else None),
            mttr_seconds=(reliability.mttr_seconds if reliability is not None else None),
            mtbf_seconds=(reliability.mtbf_seconds if reliability is not None else None),
        )
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temp = self.path.with_suffix(".tmp")
        temp.write_text(
            json.dumps(asdict(record), sort_keys=True),
            encoding="utf-8",
        )
        temp.replace(self.path)
        return record

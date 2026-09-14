from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from .lifecycle_log import LifecycleEventLog
from .resilience import ResilienceState


@dataclass(frozen=True)
class ReliabilityReport:
    observation_seconds: float
    normal_ratio: float
    cautious_ratio: float
    degraded_ratio: float
    recovery_ratio: float
    cooldown_ratio: float
    halt_ratio: float
    halt_count: int
    incident_count: int
    mttr_seconds: float | None
    mtbf_seconds: float | None
    reliability_score: float


def evaluate_reliability(
    lifecycle_log: LifecycleEventLog,
    current_state: ResilienceState,
    *,
    now_utc: datetime | None = None,
) -> ReliabilityReport:
    now_utc = now_utc or datetime.now(UTC)
    events = [
        event
        for event in lifecycle_log.list()
        if event.event == "resilience_transition"
    ]
    if not events:
        return ReliabilityReport(
            observation_seconds=0.0,
            normal_ratio=1.0 if current_state.mode == "NORMAL" else 0.0,
            cautious_ratio=0.0,
            degraded_ratio=0.0,
            recovery_ratio=0.0,
            cooldown_ratio=0.0,
            halt_ratio=1.0 if current_state.mode == "HALT" else 0.0,
            halt_count=int(current_state.mode == "HALT"),
            incident_count=int(current_state.mode != "NORMAL"),
            mttr_seconds=None,
            mtbf_seconds=None,
            reliability_score=100.0 if current_state.mode == "NORMAL" else 0.0,
        )

    parsed: list[tuple[datetime, str, str]] = []
    for event in events:
        timestamp = datetime.fromisoformat(event.created_at_utc)
        if timestamp.tzinfo is None:
            timestamp = timestamp.replace(tzinfo=UTC)
        parsed.append(
            (
                timestamp,
                str(event.metadata.get("from_mode", "")),
                str(event.metadata.get("to_mode", "")),
            )
        )
    parsed.sort(key=lambda item: item[0])

    durations = {
        "NORMAL": 0.0,
        "CAUTIOUS": 0.0,
        "DEGRADED": 0.0,
        "RECOVERY": 0.0,
        "COOLDOWN": 0.0,
        "HALT": 0.0,
    }
    for index, (started, _from_mode, to_mode) in enumerate(parsed):
        ended = parsed[index + 1][0] if index + 1 < len(parsed) else now_utc
        durations[to_mode] = durations.get(to_mode, 0.0) + max(
            0.0,
            (ended - started).total_seconds(),
        )

    observation = sum(durations.values())
    ratios = {
        mode: (duration / observation if observation > 0 else 0.0)
        for mode, duration in durations.items()
    }

    halt_count = sum(to_mode == "HALT" for _, _, to_mode in parsed)
    incident_starts: list[datetime] = []
    recoveries: list[float] = []
    open_incident: datetime | None = None
    for timestamp, from_mode, to_mode in parsed:
        if from_mode == "NORMAL" and to_mode != "NORMAL":
            open_incident = timestamp
            incident_starts.append(timestamp)
        if to_mode == "NORMAL" and open_incident is not None:
            recoveries.append((timestamp - open_incident).total_seconds())
            open_incident = None

    mttr = sum(recoveries) / len(recoveries) if recoveries else None
    gaps = [
        (incident_starts[index] - incident_starts[index - 1]).total_seconds()
        for index in range(1, len(incident_starts))
    ]
    mtbf = sum(gaps) / len(gaps) if gaps else None

    penalty = (
        ratios["CAUTIOUS"] * 10.0
        + ratios["DEGRADED"] * 35.0
        + ratios["RECOVERY"] * 20.0
        + ratios["COOLDOWN"] * 30.0
        + ratios["HALT"] * 60.0
        + min(20.0, halt_count * 4.0)
    )
    score = max(0.0, min(100.0, 100.0 - penalty))

    return ReliabilityReport(
        observation_seconds=observation,
        normal_ratio=ratios["NORMAL"],
        cautious_ratio=ratios["CAUTIOUS"],
        degraded_ratio=ratios["DEGRADED"],
        recovery_ratio=ratios["RECOVERY"],
        cooldown_ratio=ratios["COOLDOWN"],
        halt_ratio=ratios["HALT"],
        halt_count=halt_count,
        incident_count=len(incident_starts),
        mttr_seconds=mttr,
        mtbf_seconds=mtbf,
        reliability_score=score,
    )

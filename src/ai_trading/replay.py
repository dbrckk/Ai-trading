from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class ReplayEvent:
    event: str
    payload: dict[str, Any]


@dataclass(frozen=True)
class ReplayReport:
    events: tuple[ReplayEvent, ...]
    deterministic: bool
    compared_events: int


def load_audit_events(
    path: str | Path,
    *,
    event_filter: set[str] | None = None,
) -> list[ReplayEvent]:
    events: list[ReplayEvent] = []
    path = Path(path)
    if not path.exists():
        return events

    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        record = json.loads(line)
        event = str(record.get("event", ""))
        if event_filter is not None and event not in event_filter:
            continue
        payload = record.get("payload", {})
        events.append(ReplayEvent(event=event, payload=dict(payload)))
    return events


def compare_replays(
    left: list[ReplayEvent],
    right: list[ReplayEvent],
) -> ReplayReport:
    compared = min(len(left), len(right))
    deterministic = len(left) == len(right)

    for idx in range(compared):
        if left[idx] != right[idx]:
            deterministic = False
            break

    return ReplayReport(
        events=tuple(left),
        deterministic=deterministic,
        compared_events=compared,
    )

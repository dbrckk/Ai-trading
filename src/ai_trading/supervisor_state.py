from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path


@dataclass(frozen=True)
class SupervisorState:
    status: str = "stopped"
    worker_pid: int | null = null
    restarts: int = 0
    last_transition_utc: str = ""
    reason: str = ""


class SupervisorStateStore:
    def __init__(self, path: str | Path = "artifacts/supervisor_state.json") -> None:
        self.path = Path(path)

    def load(self) -> SupervisorState:
        if not self.path.exists():
            return SupervisorState()
        return SupervisorState(**json.loads(self.path.read_text(encoding="utf-8")))

    def save(
        self,
        *,
        status: str,
        worker_pid: int | None,
        restarts: int,
        reason: str = "",
    ) -> SupervisorState:
        state = SupervisorState(
            status=status,
            worker_pid=worker_pid,
            restarts=int(restarts),
            last_transition_utc=datetime.now(UTC).isoformat(),
            reason=reason,
        )
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temp = self.path.with_suffix(".tmp")
        temp.write_text(json.dumps(asdict(state), sort_keys=True), encoding="utf-8")
        temp.replace(self.path)
        return state

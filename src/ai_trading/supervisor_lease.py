from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path


@dataclass(frozen=True)
class SupervisorLease:
    owner_pid: int
    acquired_at_utc: str
    token: str


class SupervisorLeaseStore:
    def __init__(self, path: str | Path = "artifacts/supervisor_lease.json") -> None:
        self.path = Path(path)

    def load(self) -> SupervisorLease | None:
        if not self.path.exists():
            return None
        return SupervisorLease(**json.loads(self.path.read_text(encoding="utf-8")))

    @staticmethod
    def pid_alive(pid: int) -> bool:
        if pid <= 0:
            return False
        try:
            os.kill(pid, 0)
        except OSError:
            return False
        return True

    def acquire(self, token: str) -> SupervisorLease:
        current = self.load()
        if current is not None and self.pid_alive(current.owner_pid):
            raise RuntimeError(
                f"supervisor lease already owned by pid {current.owner_pid}"
            )

        lease = SupervisorLease(
            owner_pid=os.getpid(),
            acquired_at_utc=datetime.now(UTC).isoformat(),
            token=token,
        )
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temp = self.path.with_suffix(".tmp")
        temp.write_text(json.dumps(asdict(lease), sort_keys=True), encoding="utf-8")
        temp.replace(self.path)
        return lease

    def release(self, token: str) -> None:
        current = self.load()
        if current is None:
            return
        if current.token != token:
            raise RuntimeError("cannot release supervisor lease owned by another token")
        self.path.unlink(missing_ok=True)

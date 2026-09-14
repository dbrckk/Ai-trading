from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from .audit_chain import verify_audit_chain
from .audit_integrity import verify_jsonl_audit
from .champions import ChampionRegistry
from .governor_state_store import GovernorState, GovernorStateStore
from .lifecycle_log import LifecycleEventLog, sha256_file
from .readiness_score import ReadinessHistoryStore
from .state_snapshot import AtomicSnapshotStore


@dataclass(frozen=True)
class StartupCheckReport:
    ready: bool
    reasons: tuple[str, ...]
    snapshot_available: bool
    audit_valid: bool
    state_files_valid: bool
    jsonl_files_valid: bool
    active_artifact_valid: bool


def run_startup_check(
    *,
    audit_path: str | Path,
    state_files: list[str | Path],
    snapshot_store: AtomicSnapshotStore,
    governor_store: GovernorStateStore,
    jsonl_files: list[str | Path] | None = None,
    champion_registry: ChampionRegistry | None = None,
    lifecycle_log: LifecycleEventLog | None = None,
    readiness_history_store: ReadinessHistoryStore | None = None,
) -> StartupCheckReport:
    reasons: list[str] = []

    audit_path = Path(audit_path)
    if audit_path.exists():
        json_report = verify_jsonl_audit(audit_path)
        chain_report = verify_audit_chain(audit_path)
        audit_valid = json_report.valid and chain_report.valid
        if not audit_valid:
            reasons.append("audit integrity check failed")
    else:
        audit_valid = True

    state_files_valid = True
    for item in state_files:
        path = Path(item)
        if not path.exists():
            continue
        try:
            json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            state_files_valid = False
            reasons.append(f"invalid state file: {path.name}")

    jsonl_files_valid = True
    for item in jsonl_files or []:
        path = Path(item)
        if not path.exists():
            continue
        try:
            with path.open("r", encoding="utf-8") as handle:
                for line in handle:
                    if line.strip():
                        json.loads(line)
        except (OSError, json.JSONDecodeError):
            jsonl_files_valid = False
            reasons.append(f"invalid jsonl file: {path.name}")

    if readiness_history_store is not None:
        chain = readiness_history_store.verify_chain()
        if not chain.valid:
            jsonl_files_valid = False
            reasons.append("readiness history integrity check failed")

    active_artifact_valid = True
    if champion_registry is not None and lifecycle_log is not None:
        active = champion_registry.active()
        if active is not None:
            promotions = [
                event
                for event in lifecycle_log.list()
                if event.event == "promotion" and event.version == active.version
            ]
            if promotions:
                event = promotions[-1]
                if event.artifact_sha256 is not None:
                    if event.artifact_path is None:
                        active_artifact_valid = False
                        reasons.append("active champion artifact path missing")
                    else:
                        artifact = Path(event.artifact_path)
                        if (
                            not artifact.exists()
                            or sha256_file(artifact) != event.artifact_sha256
                        ):
                            active_artifact_valid = False
                            reasons.append("active champion artifact integrity check failed")

    snapshot_available = snapshot_store.latest_valid() is not None
    ready = (
        audit_valid
        and state_files_valid
        and jsonl_files_valid
        and active_artifact_valid
    )

    if not ready:
        governor_store.save(
            GovernorState(
                verdict="HALT",
                reason="startup self-check failed: " + "; ".join(reasons),
                consecutive_halts=1,
            )
        )

    return StartupCheckReport(
        ready=ready,
        reasons=tuple(reasons),
        snapshot_available=snapshot_available,
        audit_valid=audit_valid,
        state_files_valid=state_files_valid,
        jsonl_files_valid=jsonl_files_valid,
        active_artifact_valid=active_artifact_valid,
    )

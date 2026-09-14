from pathlib import Path

from ai_trading.lifecycle_log import LifecycleEventLog, sha256_file


def test_lifecycle_log_hashes_artifact_and_appends_events(tmp_path: Path) -> None:
    artifact = tmp_path / "model.joblib"
    artifact.write_bytes(b"model-bytes")
    log = LifecycleEventLog(tmp_path / "lifecycle.jsonl")

    first = log.append(
        event="promotion",
        version="v2",
        model_name="ensemble",
        artifact_path=artifact,
    )
    second = log.append(
        event="rollback",
        version="v2",
        model_name="ensemble",
        reason="degraded",
        failure_type="performance_failure",
    )

    records = log.list()
    assert records == [first, second]
    assert first.artifact_sha256 == sha256_file(artifact)
    assert second.failure_type == "performance_failure"

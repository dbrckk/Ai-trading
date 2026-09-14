import subprocess
import sys
from pathlib import Path

from ai_trading.watchdog import HeartbeatStore
from ai_trading.worker_monitor import WorkerMonitorConfig, monitor_worker


def test_worker_monitor_stops_process_without_heartbeat(tmp_path: Path) -> None:
    process = subprocess.Popen(
        [sys.executable, "-c", "import time; time.sleep(5)"]
    )
    result = monitor_worker(
        process,
        heartbeat_store=HeartbeatStore(tmp_path / "heartbeat.json"),
        config=WorkerMonitorConfig(
            poll_seconds=0.01,
            startup_grace_seconds=0.02,
            heartbeat_max_age_seconds=0.01,
        ),
    )
    assert result.forced_stop
    assert result.reason == "worker heartbeat stale"

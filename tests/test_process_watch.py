import subprocess
import sys

from ai_trading.process_watch import wait_with_timeout


def test_process_watch_times_out_and_stops_worker() -> None:
    process = subprocess.Popen(
        [sys.executable, "-c", "import time; time.sleep(2)"]
    )
    result = wait_with_timeout(process, timeout_seconds=0.05)
    assert result.timed_out
    assert process.poll() is not None

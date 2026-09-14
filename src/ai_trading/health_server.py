from __future__ import annotations

import json
from dataclasses import asdict
from http.server import BaseHTTPRequestHandler, HTTPServer
from threading import Thread

from .control_plane import read_control_plane
from .watchdog import HeartbeatStore, heartbeat_is_stale


class HealthHandler(BaseHTTPRequestHandler):
    heartbeat_store = HeartbeatStore("artifacts/multiasset_heartbeat.json")

    def do_GET(self) -> None:
        if self.path not in {"/health", "/ready"}:
            self.send_response(404)
            self.end_headers()
            return

        control = read_control_plane()
        heartbeat = self.heartbeat_store.load()
        stale = heartbeat_is_stale(heartbeat)

        payload = {
            "governor": control.governor_verdict,
            "crisis_mode": control.crisis_mode,
            "scheduler_should_run": control.scheduler_should_run,
            "heartbeat_stale": stale,
            "ready": control.scheduler_should_run and not stale,
        }

        status = 200 if payload["ready"] else 503
        body = json.dumps(payload, sort_keys=True).encode("utf-8")

        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args) -> None:
        return


class HealthServer:
    def __init__(self, host: str = "127.0.0.1", port: int = 8765) -> None:
        self.server = HTTPServer((host, port), HealthHandler)
        self.thread: Thread | None = None

    def start(self) -> None:
        if self.thread is not None:
            return
        self.thread = Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def stop(self) -> None:
        self.server.shutdown()
        self.server.server_close()
        if self.thread is not None:
            self.thread.join(timeout=2.0)
            self.thread = None

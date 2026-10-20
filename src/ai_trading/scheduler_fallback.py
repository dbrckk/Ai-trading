"""Authenticated GitHub scheduler fallback using Render as the single DB writer.

The dashboard owns the Neon connection; GitHub never receives database credentials.
"""

from __future__ import annotations

import argparse
import json
import math
import os
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class FallbackFailure(RuntimeError):
    """Sanitized failure suitable for public CI logs."""


_CLOUDFLARE_HEALTHY_WINDOW_SECONDS = 32 * 60


def _recent_cloudflare(payload: object) -> bool:
    if not isinstance(payload, dict):
        return False
    age = payload.get("last_delivery_age_seconds")
    return (
        payload.get("last_source") == "cloudflare"
        and payload.get("last_status_code") == 200
        and payload.get("last_ok") is True
        and isinstance(age, (int, float))
        and not isinstance(age, bool)
        and math.isfinite(age)
        and 0 <= age <= _CLOUDFLARE_HEALTHY_WINDOW_SECONDS
    )


def run_fallback(
    base_url: str,
    token: str,
    *,
    timeout: float = 180.0,
    opener=urlopen,
) -> str:
    """Skip a recent successful Cloudflare cycle, or trigger one paper-only cycle."""
    if not base_url.startswith("https://") or not base_url.rstrip("/"):
        raise FallbackFailure("dashboard URL must use HTTPS")
    if not token.strip():
        raise FallbackFailure("AI_TRADING_SCHEDULER_TOKEN repository secret is required")
    if not math.isfinite(timeout) or timeout <= 0:
        raise ValueError("timeout must be positive and finite")

    origin = base_url.rstrip("/")
    status_request = Request(
        origin + "/api/scheduler",
        headers={"Accept": "application/json", "User-Agent": "ai-trading-github-fallback/1"},
    )
    # Do not spend the execution budget waiting on optional scheduler telemetry.
    # Allow a slower cold-starting Render service to complete the actual cycle.
    status_timeout = min(timeout, 45.0)
    try:
        with opener(status_request, timeout=status_timeout) as response:
            status_payload = (
                json.loads(response.read(16_385))
                if response.status == 200
                else None
            )
    except (HTTPError, URLError, OSError, TimeoutError, ValueError, UnicodeError):
        status_payload = None

    if _recent_cloudflare(status_payload):
        return "skipped_recent_cloudflare"

    cycle_request = Request(
        origin + "/internal/paper-cycle",
        method="POST",
        headers={
            "Authorization": "Bearer " + token,
            "X-Scheduler-Source": "github",
            "User-Agent": "ai-trading-github-fallback/1",
        },
    )
    try:
        with opener(cycle_request, timeout=timeout) as response:
            if response.status != 200:
                raise FallbackFailure(f"paper cycle endpoint returned HTTP {response.status}")
            body = response.read(16_385)
    except HTTPError as exc:
        raise FallbackFailure(f"paper cycle endpoint returned HTTP {exc.code}") from None
    except (URLError, OSError, TimeoutError):
        raise FallbackFailure("paper cycle endpoint unavailable") from None

    if len(body) > 16_384:
        raise FallbackFailure("paper cycle response too large")
    try:
        payload = json.loads(body)
    except (ValueError, UnicodeError):
        raise FallbackFailure("paper cycle response invalid") from None
    if not isinstance(payload, dict) or payload.get("ok") is not True:
        raise FallbackFailure("paper cycle was not successful")
    return "executed"


def main() -> int:
    parser = argparse.ArgumentParser(description="Neon-budgeted paper scheduler fallback")
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--timeout", type=float, default=180.0)
    args = parser.parse_args()
    try:
        outcome = run_fallback(
            args.base_url, os.getenv("AI_TRADING_SCHEDULER_TOKEN", ""), timeout=args.timeout
        )
    except FallbackFailure as exc:
        print(f"::error::{exc}", flush=True)
        return 1
    print(f"Paper scheduler fallback: {outcome}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

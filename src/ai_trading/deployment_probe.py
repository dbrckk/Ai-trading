"""Read-only probe of the deployed dashboard; no broker or scheduler requests."""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


@dataclass(frozen=True)
class ProbeCheck:
    endpoint: str
    ok: bool
    detail: str


def _fetch_json(base_url: str, endpoint: str, timeout: float) -> tuple[dict, str]:
    request = Request(
        base_url.rstrip("/") + endpoint,
        headers={"User-Agent": "ai-trading-dashboard-uptime/1", "Accept": "application/json"},
    )
    try:
        with urlopen(request, timeout=timeout) as response:
            status = response.status
            body = response.read(128_001)
    except HTTPError as exc:
        return {}, f"http_{exc.code}"
    except (URLError, TimeoutError, OSError):
        return {}, "connection_failed"

    if status != 200:
        return {}, f"http_{status}"
    if len(body) > 128_000:
        return {}, "response_too_large"
    try:
        payload = json.loads(body)
    except (ValueError, UnicodeDecodeError):
        return {}, "invalid_json"
    if not isinstance(payload, dict):
        return {}, "invalid_payload"
    return payload, "ok"


def probe_dashboard(base_url: str, *, timeout: float = 60.0) -> tuple[ProbeCheck, ...]:
    """Check web process, durable readiness and three market cards independently."""
    if timeout <= 0:
        raise ValueError("timeout must be positive")

    checks: list[ProbeCheck] = []
    for endpoint in ("/livez", "/readyz", "/api/markets"):
        payload, fetch_state = _fetch_json(base_url, endpoint, timeout)
        if fetch_state != "ok":
            checks.append(ProbeCheck(endpoint, False, fetch_state))
            continue

        if endpoint == "/livez":
            valid = payload.get("web_healthy") is True
            detail = "web_healthy" if valid else "liveness_unhealthy"
        elif endpoint == "/readyz":
            valid = (
                payload.get("ready") is True
                and payload.get("storage_healthy") is True
            )
            detail = "storage_ready" if valid else "storage_or_configuration_unready"
        else:
            markets = payload.get("markets")
            symbols = (
                {item.get("symbol") for item in markets if isinstance(item, dict)}
                if isinstance(markets, list)
                else set()
            )
            expected = {"GC=F", "^GDAXI", "BTC-USD"}
            valid = expected.issubset(symbols)
            detail = "three_markets_present" if valid else "missing_market_cards"
        checks.append(ProbeCheck(endpoint, valid, detail))
    return tuple(checks)


def main() -> int:
    parser = argparse.ArgumentParser(description="Probe read-only Trading AI endpoints")
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--timeout", type=float, default=60.0)
    args = parser.parse_args()
    checks = probe_dashboard(args.base_url, timeout=args.timeout)
    for check in checks:
        print(
            f"{'PASS' if check.ok else 'FAIL'} {check.endpoint}: {check.detail}",
            flush=True,
        )
    return 0 if all(check.ok for check in checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())

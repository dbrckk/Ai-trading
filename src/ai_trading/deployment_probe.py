"""Read-only probe of the deployed dashboard; no broker or scheduler requests."""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from re import fullmatch
from time import sleep
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

_STARTING_RECHECKS = 3
_STARTING_RECHECK_DELAY_SECONDS = 15.0
_TRANSIENT_STARTING_MARKETS = {
    "BTC-USD:STARTING", "GC=F:STARTING", "^GDAXI:STARTING",
}


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
        # Only surface known, public readiness error codes. Never print
        # arbitrary upstream bodies, database URLs or exception details.
        if endpoint == "/readyz" and exc.code == 503:
            try:
                explanation = json.loads(exc.read(4096))
                reason = explanation.get("error") if isinstance(explanation, dict) else None
                if reason in {"storage unavailable", "configuration incomplete"}:
                    return {}, "http_503_" + reason.replace(" ", "_")
            except (ValueError, UnicodeDecodeError, OSError):
                pass
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


def _probe_endpoint(
    base_url: str,
    endpoint: str,
    timeout: float,
    *,
    expected_sha: str | None,
    require_running_markets: bool,
) -> ProbeCheck:
    payload, fetch_state = _fetch_json(base_url, endpoint, timeout)
    if fetch_state != "ok":
        return ProbeCheck(endpoint, False, fetch_state)

    if endpoint == "/livez":
        valid = payload.get("web_healthy") is True
        detail = "web_healthy" if valid else "liveness_unhealthy"
        if valid and expected_sha is not None:
            valid = payload.get("deployed_commit") == expected_sha
            detail = (
                "deployed_commit_verified"
                if valid else "deployed_commit_missing_or_mismatched"
            )
    elif endpoint == "/readyz":
        valid = (
            payload.get("ready") is True
            and payload.get("storage_healthy") is True
        )
        detail = "storage_ready" if valid else "storage_or_configuration_unready"
    else:
        markets = payload.get("markets")
        symbols = (
            {
                item["symbol"] for item in markets
                if isinstance(item, dict) and isinstance(item.get("symbol"), str)
            }
            if isinstance(markets, list)
            else set()
        )
        expected = {"GC=F", "^GDAXI", "BTC-USD"}
        portfolio = payload.get("portfolio")
        complete = (
            isinstance(portfolio, dict)
            and portfolio.get("equity_complete") is True
            and portfolio.get("error_markets") == 0
        )
        valid = expected.issubset(symbols) and complete
        if not expected.issubset(symbols):
            detail = "missing_market_cards"
        elif not complete:
            detail = "portfolio_or_market_unavailable"
        elif require_running_markets:
            # A complete portfolio alone can still report three STARTING
            # engines during a stuck scheduler cycle. Check individual
            # runtime health as well as the portfolio aggregate.
            by_symbol = {
                item["symbol"]: item
                for item in markets
                if isinstance(item, dict)
                and isinstance(item.get("symbol"), str)
                and item["symbol"] in expected
            }
            running = portfolio.get("running_markets") == len(expected)
            engines = all(
                isinstance(by_symbol[symbol].get("overview"), dict)
                and by_symbol[symbol]["overview"].get("engine_status") == "RUNNING"
                and by_symbol[symbol]["overview"].get("consecutive_cycle_errors") == 0
                for symbol in expected
            )
            valid = running and engines
            if valid:
                detail = "three_markets_running"
            else:
                # Only fixed, expected symbols and sanitized states enter CI logs.
                # Identify which engine failed without exposing arbitrary API data.
                safe_states = {"RUNNING", "STARTING", "STALE", "ERROR", "OFF", "UNKNOWN"}
                failures = []
                for symbol in sorted(expected):
                    overview = by_symbol[symbol].get("overview")
                    status = (
                        overview.get("engine_status")
                        if isinstance(overview, dict)
                        else None
                    )
                    state = status if isinstance(status, str) and status in safe_states else "UNKNOWN"
                    errors = (
                        overview.get("consecutive_cycle_errors")
                        if isinstance(overview, dict)
                        else None
                    )
                    if state != "RUNNING" or errors != 0:
                        failures.append(f"{symbol}:{state}")
                detail = (
                    "market_engines_not_running:" + ",".join(failures)
                    if failures
                    else "market_running_count_mismatch"
                )
        else:
            detail = "three_market_cards_available"
    return ProbeCheck(endpoint, valid, detail)


def _only_transient_market_starting(detail: str) -> bool:
    """Retry only known markets reported STARTING, never a mixed ERROR/STALE."""
    prefix = "market_engines_not_running:"
    if not detail.startswith(prefix):
        return False
    failures = detail.removeprefix(prefix).split(",")
    return bool(failures) and all(
        failure in _TRANSIENT_STARTING_MARKETS for failure in failures
    )


def probe_dashboard(
    base_url: str,
    *,
    timeout: float = 60.0,
    expected_sha: str | None = None,
    require_running_markets: bool = False,
) -> tuple[ProbeCheck, ...]:
    """Check web, storage and markets; optionally require healthy live engines."""
    if timeout <= 0:
        raise ValueError("timeout must be positive")
    if expected_sha is not None and fullmatch(r"[0-9a-f]{40}", expected_sha) is None:
        raise ValueError("expected_sha must be a lowercase 40-character Git SHA")

    checks = [
        _probe_endpoint(
            base_url,
            endpoint,
            timeout,
            expected_sha=expected_sha,
            require_running_markets=require_running_markets,
        )
        for endpoint in ("/livez", "/readyz", "/api/markets")
    ]
    # The free-tier host can briefly refuse the first connection while other
    # endpoints recover. Retry only transport failures, once, after the first
    # pass. HTTP errors, unhealthy payloads and SHA mismatches still fail.
    for index, check in enumerate(checks):
        if check.detail == "connection_failed":
            checks[index] = _probe_endpoint(
                base_url,
                check.endpoint,
                min(timeout, 10.0),
                expected_sha=expected_sha,
                require_running_markets=require_running_markets,
            )
    # A successful Cloudflare paper cycle can briefly mark one or more
    # workers STARTING while it persists fresh states. One read during that
    # in-flight operation is not evidence of a stuck engine. Read-only retries
    # suppress this specific false alarm, but persistent STARTING or any
    # actual ERROR/STALE/storage failure must still fail closed.
    market_index = 2
    for _ in range(_STARTING_RECHECKS):
        if not (
            require_running_markets
            and _only_transient_market_starting(checks[market_index].detail)
        ):
            break
        sleep(_STARTING_RECHECK_DELAY_SECONDS)
        checks[market_index] = _probe_endpoint(
            base_url,
            "/api/markets",
            min(timeout, 20.0),
            expected_sha=expected_sha,
            require_running_markets=True,
        )
    return tuple(checks)


def main() -> int:
    parser = argparse.ArgumentParser(description="Probe read-only Trading AI endpoints")
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--timeout", type=float, default=60.0)
    parser.add_argument(
        "--expected-sha", help="Require this exact 40-character deployed Git commit"
    )
    parser.add_argument(
        "--require-running-markets",
        action="store_true",
        help="Fail if Gold, DAX or BTC is STARTING, STALE, ERROR or has cycle errors",
    )
    args = parser.parse_args()
    checks = probe_dashboard(
        args.base_url,
        timeout=args.timeout,
        expected_sha=args.expected_sha,
        require_running_markets=args.require_running_markets,
    )
    for check in checks:
        print(
            f"{'PASS' if check.ok else 'FAIL'} {check.endpoint}: {check.detail}",
            flush=True,
        )
    return 0 if all(check.ok for check in checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())

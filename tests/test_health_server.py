import urllib.error
import urllib.request

from ai_trading.health_server import HealthServer


def test_health_server_exposes_metrics() -> None:
    server = HealthServer(host="127.0.0.1", port=0)
    server.start()
    try:
        port = server.server.server_address[1]
        with urllib.request.urlopen(
            f"http://127.0.0.1:{port}/metrics",
            timeout=2.0,
        ) as response:
            body = response.read().decode("utf-8")
            assert response.status == 200
            assert "ai_trading_governor_" in body
    finally:
        server.stop()


def test_health_server_returns_not_found_for_unknown_route() -> None:
    server = HealthServer(host="127.0.0.1", port=0)
    server.start()
    try:
        port = server.server.server_address[1]
        try:
            urllib.request.urlopen(
                f"http://127.0.0.1:{port}/unknown",
                timeout=2.0,
            )
        except urllib.error.HTTPError as exc:
            assert exc.code == 404
        else:
            raise AssertionError("expected HTTP 404")
    finally:
        server.stop()

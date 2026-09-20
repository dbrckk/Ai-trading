from __future__ import annotations

import json
import socket
import time
from threading import Thread
from urllib.error import URLError
from urllib.request import urlopen

from ai_trading.burnin import BurnInSnapshot
from ai_trading.dashboard import render_dashboard, serve_dashboard
from ai_trading.hosted_runtime import HostedPaperSettings
from ai_trading.model_quality import ModelQuality
from ai_trading.mtf_shadow_quality import MultiTimeframeShadowQuality
from ai_trading.operational_overview import build_operational_overview
from ai_trading.persistence import ModelBlob, PersistedRuntime
from ai_trading.runtime_state import RuntimeState
from ai_trading.runtime_status import HostedRuntimeStatus
from ai_trading.shadow_quality import ShadowQualityComparison
from ai_trading.trade_journal import TradeJournal

RUNTIME_KEY = "paper:GC=F:5m:online-river:v1"


class OverviewPersistence:
    def __init__(
        self,
        *,
        with_model: bool = True,
        stale: bool = False,
        cycle_errors: int = 0,
    ) -> None:
        self.runtime = PersistedRuntime(
            state=RuntimeState(
                cash=12_345.0,
                units=2.0,
                last_price=250.0,
                peak_equity=13_000.0,
                day_start_equity=12_500.0,
                last_processed="2026-09-16 05:20:00+00:00",
                processed_bars=7,
            ),
            model=(
                ModelBlob(
                    format="joblib",
                    version=1,
                    payload=b"model",
                    sha256="1234567890abcdef1234567890abcdef",
                )
                if with_model
                else None
            ),
            revision=7,
            is_new=False,
        )
        self.status = HostedRuntimeStatus(
            engine_status="STALE" if stale else "RUNNING",
            symbol="GC=F",
            interval="5m",
            updated_at_utc="2099-01-01T00:00:00+00:00",
            last_cycle_timestamp="2026-09-16T05:25:00+00:00",
            processed=True,
            side=1,
            confidence=0.8,
            approved=True,
            equity=12_845.0,
            units=2.0,
            processed_bars=7,
            poll_seconds=300.0,
            consecutive_cycle_errors=cycle_errors,
        )

    def load_runtime(self, runtime_key: str, starting_cash: float) -> PersistedRuntime:
        assert runtime_key == RUNTIME_KEY
        assert starting_cash == 100_000.0
        return self.runtime

    def list_trades(self, runtime_key: str | None = None, *, limit: int | None = None):
        assert runtime_key == RUNTIME_KEY
        assert limit == 200
        return ()

    def list_burnin_snapshots(self, runtime_key: str):
        assert runtime_key == RUNTIME_KEY
        return (
            BurnInSnapshot(
                timestamp_utc="2026-09-16T05:15:00+00:00",
                equity=12_500.0,
                scheduler_errors=0,
                regimes_covered=0,
                bootstrap_probability_positive=0.0,
                processed_bars=6,
            ),
            BurnInSnapshot(
                timestamp_utc="2026-09-16T05:20:00+00:00",
                equity=12_845.0,
                scheduler_errors=0,
                regimes_covered=0,
                bootstrap_probability_positive=0.0,
                processed_bars=7,
            ),
        )

    def list_regimes(self, runtime_key: str) -> tuple[str, ...]:
        assert runtime_key == RUNTIME_KEY
        return ("bull_normal_vol", "sideways_normal_vol")

    def load_runtime_status(self, runtime_key: str) -> HostedRuntimeStatus | None:
        assert runtime_key == RUNTIME_KEY
        return self.status

    def load_shadow_quality(self, runtime_key: str) -> ShadowQualityComparison:
        assert runtime_key == RUNTIME_KEY
        river = ModelQuality(
            score=0.60,
            accuracy=0.55,
            brier=0.30,
            directional_edge=0.05,
            observations=8,
        )
        challenger = ModelQuality(
            score=0.72,
            accuracy=0.70,
            brier=0.20,
            directional_edge=0.20,
            observations=8,
        )
        return ShadowQualityComparison(
            observations=8,
            river=river,
            challenger=challenger,
        )

    def load_mtf_shadow_quality(
        self,
        runtime_key: str,
        *,
        config_name: str | None = None,
    ) -> MultiTimeframeShadowQuality:
        assert runtime_key == RUNTIME_KEY
        assert config_name == "h45m-min5bp-atr0.25-train1000-conf56"
        river = ModelQuality(
            score=0.58,
            accuracy=0.52,
            brier=0.32,
            directional_edge=0.02,
            observations=8,
        )
        challenger = ModelQuality(
            score=0.75,
            accuracy=0.72,
            brier=0.18,
            directional_edge=0.24,
            observations=8,
        )
        return MultiTimeframeShadowQuality(
            observations=8,
            river=river,
            challenger=challenger,
            long_labels=3,
            flat_labels=3,
            short_labels=2,
        )


class ReadinessOverviewPersistence(OverviewPersistence):
    def list_burnin_snapshots(self, runtime_key: str):
        assert runtime_key == RUNTIME_KEY
        return (
            BurnInSnapshot(
                timestamp_utc="2026-09-16T05:10:00+00:00",
                equity=12_000.0,
                scheduler_errors=0,
                regimes_covered=2,
                bootstrap_probability_positive=0.0,
                processed_bars=5,
            ),
            BurnInSnapshot(
                timestamp_utc="2026-09-16T05:15:00+00:00",
                equity=12_400.0,
                scheduler_errors=0,
                regimes_covered=2,
                bootstrap_probability_positive=0.0,
                processed_bars=6,
            ),
            BurnInSnapshot(
                timestamp_utc="2026-09-16T05:20:00+00:00",
                equity=12_845.0,
                scheduler_errors=0,
                regimes_covered=2,
                bootstrap_probability_positive=0.0,
                processed_bars=7,
            ),
        )


class FailingOverviewPersistence:
    def load_runtime(self, runtime_key: str, starting_cash: float):
        del runtime_key, starting_cash
        raise RuntimeError("postgresql://user:secret@example.invalid/private")

    def load_runtime_status(self, runtime_key: str):
        del runtime_key
        raise RuntimeError("postgresql://user:secret@example.invalid/private")


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _start_overview_dashboard(persistence: OverviewPersistence) -> int:
    port = _free_port()
    thread = Thread(
        target=serve_dashboard,
        kwargs={
            "host": "127.0.0.1",
            "port": port,
            "persistence": persistence,
            "settings": HostedPaperSettings(
                enabled=False,
                symbol="GC=F",
                interval="5m",
            ),
        },
        daemon=True,
    )
    thread.start()
    deadline = time.time() + 3
    while time.time() < deadline:
        try:
            with urlopen(f"http://127.0.0.1:{port}/healthz", timeout=2) as response:
                if response.status == 200:
                    return port
        except URLError:
            time.sleep(0.02)
    raise AssertionError("dashboard server did not start")


def test_operational_overview_exposes_model_and_runtime_metadata() -> None:
    payload = build_operational_overview(OverviewPersistence(), RUNTIME_KEY)

    assert payload["storage_healthy"] is True
    assert payload["runtime_revision"] == 7
    assert payload["processed_bars"] == 7
    assert payload["last_processed"] == "2026-09-16 05:20:00+00:00"
    assert payload["model"] == {
        "present": True,
        "format": "joblib",
        "version": 1,
        "checksum": "1234567890ab",
    }
    assert payload["lag_detected"] is False
    assert payload["consecutive_cycle_errors"] == 0
    assert payload["burnin"]["samples"] == 2
    assert payload["burnin"]["processed_bars"] == 7
    assert payload["burnin"]["total_return"] > 0.0
    assert payload["burnin"]["max_drawdown"] == 0.0
    assert payload["readiness"]["available"] is False
    assert payload["shadow_challenger"]["available"] is True
    assert payload["shadow_challenger"]["observations"] == 8
    assert round(payload["shadow_challenger"]["score_delta"], 2) == 0.12
    assert payload["shadow_challenger"]["challenger"]["accuracy"] == 0.70
    assert payload["mtf_shadow_challenger"]["observations"] == 8
    assert payload["mtf_shadow_challenger"]["horizon_minutes"] == 45
    assert payload["mtf_shadow_challenger"]["candidate_config"]["config_name"] == (
        "h45m-min5bp-atr0.25-train1000-conf56"
    )
    assert payload["mtf_shadow_challenger"]["candidate_config"]["min_confidence"] == 0.56
    assert payload["mtf_shadow_challenger"]["timeframes"] == ["5m", "15m", "1h", "4h"]
    assert payload["mtf_shadow_challenger"]["promotion_gate"]["min_observations"] == 500
    assert payload["mtf_shadow_challenger"]["directional_observations"] == 5
    assert payload["mtf_shadow_challenger"]["directional_rate"] == 0.625
    assert payload["mtf_shadow_challenger"]["label_distribution"] == {
        "long": 3,
        "flat": 3,
        "short": 2,
    }
    mtf_gate = payload["mtf_shadow_challenger"]["promotion_gate"]
    assert mtf_gate["min_directional_observations"] == 100
    assert mtf_gate["eligible_for_review"] is False
    assert any("directional" in reason for reason in mtf_gate["reasons"])
    gate = payload["shadow_challenger"]["promotion_gate"]
    assert gate["eligible_for_review"] is False
    assert gate["min_observations"] == 250
    assert any("250" in reason for reason in gate["reasons"])
    assert payload["alerts"] == []


def test_operational_overview_flags_stale_runtime() -> None:
    payload = build_operational_overview(
        OverviewPersistence(stale=True),
        RUNTIME_KEY,
    )

    assert payload["lag_detected"] is True
    assert payload["alerts"] == ["worker heartbeat expired"]


def test_operational_overview_flags_missing_model_after_processing() -> None:
    payload = build_operational_overview(
        OverviewPersistence(with_model=False),
        RUNTIME_KEY,
    )

    assert payload["model"] == {
        "present": False,
        "format": None,
        "version": None,
        "checksum": None,
    }
    assert payload["alerts"] == ["model missing for initialized runtime"]


def test_operational_overview_flags_inconsistent_runtime() -> None:
    persistence = OverviewPersistence()
    persistence.runtime = PersistedRuntime(
        state=RuntimeState(
            cash=12_345.0,
            units=2.0,
            last_price=250.0,
            peak_equity=13_000.0,
            day_start_equity=12_500.0,
            last_processed=None,
            processed_bars=7,
        ),
        model=persistence.runtime.model,
        revision=7,
        is_new=False,
    )

    payload = build_operational_overview(persistence, RUNTIME_KEY)

    assert payload["alerts"] == ["runtime inconsistent"]


def test_operational_overview_storage_failure_is_sanitized() -> None:
    payload = build_operational_overview(FailingOverviewPersistence(), RUNTIME_KEY)

    assert payload == {
        "storage_healthy": False,
        "engine_status": "ERROR",
        "runtime_revision": None,
        "processed_bars": None,
        "last_processed": None,
        "lag_detected": False,
        "consecutive_cycle_errors": None,
        "model": {
            "present": False,
            "format": None,
            "version": None,
            "checksum": None,
        },
        "burnin": {
            "samples": 0,
            "processed_bars": 0,
            "total_return": None,
            "max_drawdown": None,
        },
        "readiness": {
            "available": False,
            "ready": None,
            "checks_passed": None,
            "checks_total": 8,
            "checks": [],
        },
        "shadow_challenger": {
            "available": False,
            "status": "collecting",
            "observations": 0,
            "score_delta": None,
            "river": None,
            "challenger": None,
            "promotion_gate": {
                "eligible_for_review": False,
                "min_observations": 250,
                "reasons": [
                    "need at least 250 realized shadow observations"
                ],
            },
        },
        "mtf_shadow_challenger": {
            "available": False,
            "status": "collecting",
            "candidate_config": {
                "symbol": "GC=F",
                "config_name": "h45m-min5bp-atr0.25-train1000-conf56",
                "horizon_bars": 9,
                "minimum_threshold": 0.0005,
                "atr_multiplier": 0.25,
                "max_train_rows": 1000,
                "min_confidence": 0.56,
                "min_train_rows": 500,
                "feature_warmup_rows": 600,
            },
            "observations": 0,
            "directional_observations": 0,
            "directional_rate": 0.0,
            "label_distribution": {"long": 0, "flat": 0, "short": 0},
            "score_delta": None,
            "river": None,
            "challenger": None,
            "horizon_minutes": 45,
            "timeframes": ["5m", "15m", "1h", "4h"],
            "label": {
                "type": "volatility_adaptive",
                "minimum_threshold": 0.0005,
                "atr_multiplier": 0.25,
            },
            "promotion_gate": {
                "eligible_for_review": False,
                "min_observations": 500,
                "min_directional_observations": 100,
                "reasons": [
                    "need at least 500 realized MTF observations",
                    "need at least 100 directional MTF observations",
                ],
            },
        },
        "alerts": ["storage unavailable"],
    }
    assert "secret" not in repr(payload)
    assert "example.invalid" not in repr(payload)


def test_dashboard_exposes_operational_overview_endpoint() -> None:
    port = _start_overview_dashboard(OverviewPersistence())

    with urlopen(f"http://127.0.0.1:{port}/api/overview", timeout=2) as response:
        payload = json.loads(response.read().decode())

    assert response.status == 200
    assert payload["runtime_revision"] == 7
    assert payload["model"]["present"] is True
    assert payload["model"]["checksum"] == "1234567890ab"
    assert payload["burnin"]["processed_bars"] == 7
    assert payload["burnin"]["samples"] == 2
    assert payload["shadow_challenger"]["observations"] == 8
    assert payload["shadow_challenger"]["available"] is True
    assert payload["mtf_shadow_challenger"]["observations"] == 8
    assert payload["mtf_shadow_challenger"]["available"] is True
    assert payload["alerts"] == []


def test_dashboard_renders_model_and_revision_metadata(tmp_path) -> None:
    page = render_dashboard(
        TradeJournal(tmp_path / "empty.jsonl"),
        persistence=OverviewPersistence(),
        runtime_key=RUNTIME_KEY,
    )

    assert '<small>Runtime revision</small><strong>7</strong>' in page
    assert '<small>Consecutive cycle errors</small><strong>0</strong>' in page
    assert '<small>Model</small><strong>joblib v1</strong>' in page
    assert '<small>Model checksum</small><strong>1234567890ab</strong>' in page
    assert "Operational alerts: none" in page


def test_dashboard_renders_operational_alerts(tmp_path) -> None:
    page = render_dashboard(
        TradeJournal(tmp_path / "empty.jsonl"),
        persistence=OverviewPersistence(with_model=False, stale=True),
        runtime_key=RUNTIME_KEY,
    )

    assert "Operational alerts: worker heartbeat expired · model missing for initialized runtime" in page


def test_dashboard_renders_inconsistent_runtime_alert(tmp_path) -> None:
    persistence = OverviewPersistence()
    persistence.runtime = PersistedRuntime(
        state=RuntimeState(
            cash=12_345.0,
            units=2.0,
            last_price=250.0,
            peak_equity=13_000.0,
            day_start_equity=12_500.0,
            last_processed=None,
            processed_bars=7,
        ),
        model=persistence.runtime.model,
        revision=7,
        is_new=False,
    )

    page = render_dashboard(
        TradeJournal(tmp_path / "empty.jsonl"),
        persistence=persistence,
        runtime_key=RUNTIME_KEY,
    )

    assert "Operational alerts: runtime inconsistent" in page


def test_operational_overview_flags_cycle_reliability_degradation() -> None:
    payload = build_operational_overview(
        OverviewPersistence(cycle_errors=2),
        RUNTIME_KEY,
    )

    assert payload["consecutive_cycle_errors"] == 2
    assert payload["alerts"] == ["paper cycle reliability degraded"]


def test_dashboard_renders_cycle_reliability_alert(tmp_path) -> None:
    page = render_dashboard(
        TradeJournal(tmp_path / "empty.jsonl"),
        persistence=OverviewPersistence(cycle_errors=2),
        runtime_key=RUNTIME_KEY,
    )

    assert '<small>Consecutive cycle errors</small><strong>2</strong>' in page
    assert "Operational alerts: paper cycle reliability degraded" in page


def test_operational_overview_exposes_structured_readiness() -> None:
    payload = build_operational_overview(ReadinessOverviewPersistence(), RUNTIME_KEY)

    readiness = payload["readiness"]
    assert readiness["available"] is True
    assert readiness["ready"] is False
    assert readiness["checks_total"] == 8
    assert len(readiness["checks"]) == 8
    assert {check["name"] for check in readiness["checks"]} == {
        "Burn-in bars",
        "Sharpe",
        "Sortino",
        "Max drawdown",
        "Total return",
        "Bootstrap confidence",
        "Regime coverage",
        "Scheduler errors",
    }
    burnin = next(
        check for check in readiness["checks"] if check["name"] == "Burn-in bars"
    )
    assert burnin["value"] == 7
    assert burnin["threshold"] == 126
    assert burnin["comparison"] == ">="
    assert burnin["passed"] is False


def test_overview_endpoint_includes_readiness_evidence() -> None:
    port = _start_overview_dashboard(ReadinessOverviewPersistence())

    with urlopen(f"http://127.0.0.1:{port}/api/overview", timeout=2) as response:
        payload = json.loads(response.read().decode())

    assert response.status == 200
    assert payload["readiness"]["available"] is True
    assert payload["readiness"]["checks_total"] == 8
    assert len(payload["readiness"]["checks"]) == 8



class BtcOverviewPersistence(OverviewPersistence):
    def load_runtime(self, runtime_key: str, starting_cash: float) -> PersistedRuntime:
        assert runtime_key == "paper:BTC-USD:5m:online-river:v1"
        assert starting_cash == 100_000.0
        return self.runtime

    def load_runtime_status(self, runtime_key: str) -> HostedRuntimeStatus | None:
        assert runtime_key == "paper:BTC-USD:5m:online-river:v1"
        return HostedRuntimeStatus(
            engine_status="RUNNING",
            symbol="BTC-USD",
            interval="5m",
            updated_at_utc="2099-01-01T00:00:00+00:00",
            poll_seconds=300.0,
        )

    def list_burnin_snapshots(self, runtime_key: str):
        del runtime_key
        return ()

    def list_regimes(self, runtime_key: str):
        del runtime_key
        return ()

    def load_shadow_quality(self, runtime_key: str) -> ShadowQualityComparison:
        del runtime_key
        return super().load_shadow_quality(RUNTIME_KEY)

    def load_mtf_shadow_quality(self, runtime_key: str, **kwargs):
        assert runtime_key == "paper:BTC-USD:5m:online-river:v1"
        assert kwargs["config_name"] == "h90m-min3bp-atr0.15-train1000-conf60"
        return super().load_mtf_shadow_quality(RUNTIME_KEY)


def test_btc_overview_exposes_validated_mtf_candidate() -> None:
    payload = build_operational_overview(
        BtcOverviewPersistence(),
        "paper:BTC-USD:5m:online-river:v1",
    )

    mtf = payload["mtf_shadow_challenger"]
    assert mtf["status"] == "comparable"
    assert mtf["candidate_config"]["config_name"] == (
        "h90m-min3bp-atr0.15-train1000-conf60"
    )
    assert mtf["candidate_config"]["minimum_threshold"] == 0.0003
    assert mtf["candidate_config"]["atr_multiplier"] == 0.15
    assert mtf["candidate_config"]["min_confidence"] == 0.60
    assert mtf["horizon_minutes"] == 90
    assert mtf["promotion_gate"]["eligible_for_review"] is False

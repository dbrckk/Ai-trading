from __future__ import annotations

from dataclasses import dataclass
from threading import Barrier

import pytest

import ai_trading.multi_market as multi_market_module
from ai_trading.dashboard import render_dashboard
from ai_trading.multi_market import (
    DEFAULT_MARKETS,
    build_multi_market_overview,
    configured_markets_from_env,
    run_multi_market_paper_cycle,
)
from ai_trading.paper_cycle import PaperCycleResult
from ai_trading.paper_cycle_service import PaperCycleServiceError
from ai_trading.persistence import PersistedRuntime
from ai_trading.runtime_state import RuntimeState
from ai_trading.runtime_status import HostedRuntimeStatus
from ai_trading.trade_journal import TradeJournal


@dataclass
class FakeMultiPersistence:
    equities: dict[str, float]

    def load_runtime(self, runtime_key: str, starting_cash: float) -> PersistedRuntime:
        assert starting_cash == 100_000.0
        symbol = runtime_key.split(":", 2)[1]
        equity = self.equities[symbol]
        return PersistedRuntime(
            state=RuntimeState(
                cash=equity,
                units=0.0,
                last_price=100.0,
                peak_equity=max(100_000.0, equity),
                day_start_equity=100_000.0,
                last_processed="2026-09-19 18:00:00+00:00",
                processed_bars=10,
            ),
            model=None,
            revision=10,
            is_new=False,
        )

    def load_runtime_status(self, runtime_key: str) -> HostedRuntimeStatus:
        symbol = runtime_key.split(":", 2)[1]
        return HostedRuntimeStatus(
            engine_status="RUNNING",
            symbol=symbol,
            interval="5m",
            updated_at_utc="2099-01-01T00:00:00+00:00",
            last_cycle_timestamp="2026-09-19 18:00:00+00:00",
            processed=True,
            side=1,
            confidence=0.72,
            reason="processed 1 bar(s)",
            processed_bars=10,
            poll_seconds=300.0,
            cycle_duration_seconds=12.3,
            mtf_evaluated=True,
        )

    def list_burnin_snapshots(self, runtime_key: str):
        del runtime_key
        return ()

    def list_regimes(self, runtime_key: str):
        del runtime_key
        return ()

    def list_trades(self, runtime_key: str | None = None, *, limit: int | None = None):
        del runtime_key, limit
        return ()

    def load_trade_performance(self, runtime_key: str):
        del runtime_key
        from ai_trading.performance_metrics import performance_metrics_from_totals

        return performance_metrics_from_totals(
            trade_count=0,
            realized_pnl=0.0,
            gross_profit=0.0,
            gross_loss=0.0,
            max_drawdown=0.0,
        )


def test_configured_markets_default_to_gold(monkeypatch) -> None:
    monkeypatch.delenv("AI_TRADING_MARKETS", raising=False)

    markets = configured_markets_from_env()

    assert [market.symbol for market in markets] == ["GC=F"]
    assert markets[0].allocation == 1.0


def test_configured_default_bundle_uses_34_33_33(monkeypatch) -> None:
    monkeypatch.setenv("AI_TRADING_MARKETS", "GC=F,^GDAXI,BTC-USD")

    markets = configured_markets_from_env()

    assert markets == DEFAULT_MARKETS
    assert sum(market.allocation for market in markets) == pytest.approx(1.0)


def test_multi_market_cycle_isolates_one_market_failure(monkeypatch) -> None:
    calls: list[tuple[str, str]] = []

    def fake_cycle(settings, *, persistence=None, **kwargs):
        del persistence, kwargs
        calls.append((settings.symbol, settings.mtf_period))
        if settings.symbol == "^GDAXI":
            raise PaperCycleServiceError(
                code="execution_failed",
                error_type="ProviderError",
            )
        return PaperCycleResult(
            processed=2,
            remaining_backlog=False,
            last_processed="2026-09-19 18:00:00+00:00",
            processed_bars=10,
            reason="processed 2 bar(s)",
        )

    monkeypatch.setattr(
        multi_market_module,
        "run_production_paper_cycle",
        fake_cycle,
    )

    result = run_multi_market_paper_cycle(
        DEFAULT_MARKETS,
        period="5d",
        interval="5m",
        max_catchup_bars=72,
        poll_seconds=300.0,
        shadow_challenger_enabled=True,
        persistence=object(),
    )

    assert sorted(calls) == sorted(
        [("GC=F", "1mo"), ("^GDAXI", "1mo"), ("BTC-USD", "1mo")]
    )
    assert result.processed == 4
    assert "isolated failures=1" in result.reason


def test_multi_market_overview_scales_normalized_sleeves_to_100k() -> None:
    backend = FakeMultiPersistence(
        equities={
            "GC=F": 110_000.0,
            "^GDAXI": 100_000.0,
            "BTC-USD": 90_000.0,
        }
    )

    snapshot = build_multi_market_overview(
        backend,
        DEFAULT_MARKETS,
        interval="5m",
        portfolio_cash=100_000.0,
    )

    assert snapshot["portfolio"]["equity"] == pytest.approx(100_100.0)
    assert snapshot["portfolio"]["pnl"] == pytest.approx(100.0)
    assert snapshot["portfolio"]["healthy_markets"] == 3
    assert [row["label"] for row in snapshot["markets"]] == [
        "Gold",
        "DAX",
        "BTC / USD",
    ]


def test_dashboard_renders_multi_market_cards(tmp_path) -> None:
    backend = FakeMultiPersistence(
        equities={
            "GC=F": 100_000.0,
            "^GDAXI": 100_000.0,
            "BTC-USD": 100_000.0,
        }
    )

    page = render_dashboard(
        TradeJournal(tmp_path / "empty.jsonl"),
        persistence=backend,
        runtime_key="paper:GC=F:5m:online-river:v1",
        markets=DEFAULT_MARKETS,
        market_interval="5m",
    )

    assert "Multi-market portfolio" in page
    assert "Gold" in page
    assert "DAX" in page
    assert "BTC / USD" in page
    assert "Healthy markets" in page
    assert "Signal" in page
    assert "Confidence" in page
    assert "LONG" in page
    assert "72.0%" in page
    assert 'class="market-card gold"' in page
    assert 'class="market-card dax"' in page
    assert 'class="market-card btc"' in page
    assert "confidence-meter" in page
    assert "5m challenger evidence" in page
    assert "MTF 45m" in page
    assert "h45m-min5bp-atr0.25-train1000-conf56" in page
    assert "h45m-min5bp-atr0.25-train1000-conf60" in page
    assert "h90m-min3bp-atr0.15-train1000-conf60" in page
    assert "MTF 90m" in page
    assert "UNVALIDATED" not in page
    assert "DISABLED" not in page
    assert "Directional MTF" in page
    assert "Directional MTF evidence" in page
    assert "5m/15m/1h/4h" in page
    assert "portfolio-ribbon" in page
    assert "PAPER ONLY" in page
    assert "Cycle latency" in page
    assert "12.3s" in page
    assert "MTF this cycle" in page
    assert "YES" in page



def test_multi_market_cycle_runs_markets_concurrently(monkeypatch) -> None:
    barrier = Barrier(len(DEFAULT_MARKETS))

    def fake_cycle(settings, *, persistence=None, **kwargs):
        del settings, persistence, kwargs
        barrier.wait(timeout=2.0)
        return PaperCycleResult(
            processed=1,
            remaining_backlog=False,
            last_processed="2026-09-19 18:00:00+00:00",
            processed_bars=5,
            reason="processed 1 bar(s)",
        )

    monkeypatch.setattr(
        multi_market_module,
        "run_production_paper_cycle",
        fake_cycle,
    )

    result = run_multi_market_paper_cycle(
        DEFAULT_MARKETS,
        period="5d",
        interval="5m",
        max_catchup_bars=72,
        poll_seconds=300.0,
        shadow_challenger_enabled=True,
        persistence=object(),
    )

    assert result.processed == 3
    assert "3 market(s)" in result.reason

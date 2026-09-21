import math

import pytest

from ai_trading.config import RiskConfig
from ai_trading.execution_costs import risk_config_for_symbol
from ai_trading.runtime import PaperAutonomousRuntime


def test_execution_cost_override_is_symbol_specific() -> None:
    raw = """
    {
      "GC=F": {"transaction_cost_bps": 1.5, "slippage_bps": 2.5},
      "BTC-USD": {"transaction_cost_bps": 4.0, "slippage_bps": 6.0}
    }
    """
    base = RiskConfig(transaction_cost_bps=2.0, slippage_bps=1.0)

    gold = risk_config_for_symbol("GC=F", base, raw=raw)
    dax = risk_config_for_symbol("^GDAXI", base, raw=raw)

    assert gold.transaction_cost_bps == 1.5
    assert gold.slippage_bps == 2.5
    assert dax == base


def test_execution_cost_override_can_be_partial() -> None:
    base = RiskConfig(transaction_cost_bps=2.0, slippage_bps=1.0)
    updated = risk_config_for_symbol(
        "GC=F",
        base,
        raw='{"GC=F": {"slippage_bps": 3.25}}',
    )

    assert updated.transaction_cost_bps == 2.0
    assert updated.slippage_bps == 3.25


@pytest.mark.parametrize(
    "raw",
    [
        "not-json",
        "[]",
        '{"GC=F": 3}',
        '{"GC=F": {"unknown": 1}}',
        '{"GC=F": {"slippage_bps": -1}}',
        '{"GC=F": {"transaction_cost_bps": "nan"}}',
    ],
)
def test_execution_cost_overrides_fail_closed_on_invalid_configuration(raw: str) -> None:
    with pytest.raises(ValueError):
        risk_config_for_symbol("GC=F", raw=raw)


def test_default_runtime_uses_symbol_cost_override(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv(
        "AI_TRADING_EXECUTION_COSTS_JSON",
        '{"GC=F": {"transaction_cost_bps": 7.0, "slippage_bps": 8.0}}',
    )

    runtime = PaperAutonomousRuntime(
        symbol="GC=F",
        online_model_path=tmp_path / "model.joblib",
        lock_path=tmp_path / "runtime.lock",
    )

    assert runtime.risk_config.transaction_cost_bps == 7.0
    assert runtime.risk_config.slippage_bps == 8.0


def test_explicit_runtime_risk_config_has_priority(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv(
        "AI_TRADING_EXECUTION_COSTS_JSON",
        '{"GC=F": {"transaction_cost_bps": 7.0, "slippage_bps": 8.0}}',
    )
    explicit = RiskConfig(transaction_cost_bps=9.0, slippage_bps=10.0)

    runtime = PaperAutonomousRuntime(
        symbol="GC=F",
        risk_config=explicit,
        online_model_path=tmp_path / "model.joblib",
        lock_path=tmp_path / "runtime.lock",
    )

    assert runtime.risk_config == explicit

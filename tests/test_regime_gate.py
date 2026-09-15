from types import SimpleNamespace

from ai_trading.regime_gate import RegimeGatePolicy, evaluate_regime_gate


def test_regime_gate_accepts_balanced_regime_results() -> None:
    report = SimpleNamespace(
        regime_returns={
            "trend": 0.12,
            "range": 0.04,
            "high_volatility": -0.03,
        }
    )

    result = evaluate_regime_gate(report)

    assert result.passed
    assert result.observed_regimes == 3
    assert result.worst_regime == "high_volatility"


def test_regime_gate_rejects_fragile_regime_profile() -> None:
    report = SimpleNamespace(
        regime_returns={
            "trend": 0.35,
            "high_volatility": -0.20,
        }
    )

    result = evaluate_regime_gate(
        report,
        RegimeGatePolicy(
            min_observed_regimes=2,
            min_regime_return=-0.10,
            max_regime_return_spread=0.50,
        ),
    )

    assert not result.passed
    assert "worst regime return below threshold" in result.reasons
    assert "regime return dispersion above threshold" in result.reasons

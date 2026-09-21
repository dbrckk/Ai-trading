import pandas as pd
import pytest

from ai_trading.alpha_allocation import AlphaAllocationConfig
from ai_trading.config import ModelConfig, RiskConfig
from ai_trading.global_allocator import (
    GlobalAllocatorConfig,
    allocate_global_capital,
    expected_shortfall,
)
from ai_trading.portfolio import AllocationConfig
from ai_trading.portfolio_intelligence import PortfolioIntelligenceConfig
from ai_trading.portfolio_risk import PortfolioRiskConfig


@pytest.mark.parametrize(
    "factory",
    [
        lambda: RiskConfig(starting_cash=0.0),
        lambda: RiskConfig(min_confidence=1.1),
        lambda: RiskConfig(transaction_cost_bps=-1.0),
        lambda: ModelConfig(horizon_bars=0),
        lambda: ModelConfig(return_threshold=-0.001),
        lambda: AllocationConfig(max_asset_weight=0.0),
        lambda: AllocationConfig(min_asset_weight=0.5, max_asset_weight=0.4),
        lambda: PortfolioRiskConfig(max_net_exposure=1.1, max_gross_exposure=1.0),
        lambda: PortfolioRiskConfig(max_pair_correlation=1.1),
        lambda: PortfolioIntelligenceConfig(min_leverage=1.1, max_leverage=1.0),
        lambda: PortfolioIntelligenceConfig(
            correlation_soft_limit=0.9,
            correlation_hard_limit=0.8,
        ),
        lambda: AlphaAllocationConfig(min_signal_quality=1.1),
        lambda: GlobalAllocatorConfig(cvar_alpha=1.0),
        lambda: GlobalAllocatorConfig(cost_penalty=-1.0),
    ],
)
def test_invalid_strategy_configuration_fails_closed(factory) -> None:
    with pytest.raises(ValueError):
        factory()


@pytest.mark.parametrize("alpha", [0.0, 1.0, -0.1, 1.1])
def test_expected_shortfall_rejects_invalid_alpha(alpha: float) -> None:
    with pytest.raises(ValueError, match="alpha"):
        expected_shortfall(pd.Series([0.01, -0.02, 0.005]), alpha=alpha)


def test_global_allocator_rejects_negative_transaction_costs() -> None:
    returns = pd.DataFrame({"A": [0.01, -0.01, 0.02]})
    with pytest.raises(ValueError, match="transaction_cost_bps"):
        allocate_global_capital(
            returns,
            expected_alpha=pd.Series({"A": 0.01}),
            quality=pd.Series({"A": 0.8}),
            transaction_cost_bps=-1.0,
        )

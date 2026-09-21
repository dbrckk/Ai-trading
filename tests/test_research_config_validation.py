import pytest

from ai_trading.backtest import WalkForwardConfig
from ai_trading.mtf_parameter_benchmark import MTFBenchmarkConfig
from ai_trading.multiasset_backtest import MultiAssetWalkForwardBacktester


@pytest.mark.parametrize(
    "factory",
    [
        lambda: WalkForwardConfig(min_train_bars=1),
        lambda: WalkForwardConfig(test_window_bars=0),
        lambda: WalkForwardConfig(min_train_bars=100, max_train_bars=99),
        lambda: WalkForwardConfig(periods_per_year=0.0),
        lambda: MTFBenchmarkConfig(
            horizon_bars=0,
            minimum_threshold=0.001,
            atr_multiplier=0.25,
            max_train_rows=1000,
            min_confidence=0.60,
        ),
        lambda: MTFBenchmarkConfig(
            horizon_bars=9,
            minimum_threshold=-0.001,
            atr_multiplier=0.25,
            max_train_rows=1000,
            min_confidence=0.60,
        ),
        lambda: MTFBenchmarkConfig(
            horizon_bars=9,
            minimum_threshold=0.001,
            atr_multiplier=-0.25,
            max_train_rows=1000,
            min_confidence=0.60,
        ),
        lambda: MTFBenchmarkConfig(
            horizon_bars=9,
            minimum_threshold=0.001,
            atr_multiplier=0.25,
            max_train_rows=0,
            min_confidence=0.60,
        ),
        lambda: MTFBenchmarkConfig(
            horizon_bars=9,
            minimum_threshold=0.001,
            atr_multiplier=0.25,
            max_train_rows=1000,
            min_confidence=1.1,
        ),
        lambda: MultiAssetWalkForwardBacktester(min_train_bars=1),
        lambda: MultiAssetWalkForwardBacktester(test_window_bars=0),
    ],
)
def test_invalid_research_configuration_fails_closed(factory) -> None:
    with pytest.raises(ValueError):
        factory()


def test_valid_research_configurations_remain_supported() -> None:
    walk = WalkForwardConfig(
        min_train_bars=120,
        test_window_bars=40,
        max_train_bars=180,
        periods_per_year=None,
    )
    mtf = MTFBenchmarkConfig(
        horizon_bars=9,
        minimum_threshold=0.0005,
        atr_multiplier=0.25,
        max_train_rows=1000,
        min_confidence=0.60,
    )
    multi = MultiAssetWalkForwardBacktester(
        min_train_bars=120,
        test_window_bars=40,
    )

    assert walk.max_train_bars == 180
    assert mtf.horizon_minutes == 45
    assert multi.min_train_bars == 120

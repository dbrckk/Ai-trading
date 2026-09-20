from ai_trading.mtf_shadow_config import validated_mtf_shadow_config


def test_gold_uses_validated_45m_candidate() -> None:
    config = validated_mtf_shadow_config("GC=F")

    assert config is not None
    assert config.config_name == "h45m-min5bp-atr0.25-train1000-conf56"
    assert config.horizon_bars == 9
    assert config.horizon_minutes == 45
    assert config.minimum_threshold == 0.0005
    assert config.atr_multiplier == 0.25
    assert config.max_train_rows == 1000
    assert config.min_confidence == 0.56


def test_dax_uses_validated_45m_candidate() -> None:
    config = validated_mtf_shadow_config("^GDAXI")

    assert config is not None
    assert config.config_name == "h45m-min5bp-atr0.25-train1000-conf60"
    assert config.horizon_bars == 9
    assert config.horizon_minutes == 45
    assert config.minimum_threshold == 0.0005
    assert config.max_train_rows == 1000
    assert config.min_confidence == 0.60


def test_btc_has_no_validated_mtf_candidate() -> None:
    assert validated_mtf_shadow_config("BTC-USD") is None

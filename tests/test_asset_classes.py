from ai_trading.asset_classes import asset_allowed_in_mode, classify_symbol


def test_common_symbols_are_classified() -> None:
    assert classify_symbol("GC=F") == "metals"
    assert classify_symbol("CL=F") == "energy"
    assert classify_symbol("EURUSD=X") == "fx"
    assert classify_symbol("BTC-USD") == "crypto"


def test_energy_is_disabled_in_capital_preservation_by_default() -> None:
    assert asset_allowed_in_mode("GC=F", "capital-preservation")
    assert not asset_allowed_in_mode("CL=F", "capital-preservation")

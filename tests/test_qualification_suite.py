from ai_trading.qualification_suite import _chaos_cases


def test_qualification_suite_contains_baseline_and_faults() -> None:
    cases = _chaos_cases("GC=F", 10)
    names = [name for name, _ in cases]
    assert names[0] == "baseline"
    assert "ohlc_violation" in names
    assert "stale_prices" in names

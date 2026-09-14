from pathlib import Path

from ai_trading.qualification_store import QualificationStore
from ai_trading.soak import SoakResult
from ai_trading.soak_gate import evaluate_soak_qualification


def test_qualification_store_round_trip(tmp_path: Path) -> None:
    result = SoakResult(
        cycles=100,
        successes=100,
        failures=0,
        final_equity=101000.0,
        governor_verdict="TRADE",
        crisis_mode="normal",
        errors=(),
        max_drawdown=0.02,
        min_equity=99000.0,
    )
    qualification = evaluate_soak_qualification(result)
    store = QualificationStore(tmp_path / "qualification.json")
    saved = store.save(result, qualification)
    loaded = store.load()

    assert loaded == saved
    assert loaded is not None
    assert loaded.passed

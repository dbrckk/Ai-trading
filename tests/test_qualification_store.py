from pathlib import Path

from ai_trading.qualification_store import QualificationStore
from ai_trading.reliability import ReliabilityReport
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



def test_qualification_store_persists_reliability_sla(tmp_path: Path) -> None:
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
    reliability = ReliabilityReport(
        observation_seconds=86_400.0,
        normal_ratio=0.97,
        cautious_ratio=0.01,
        degraded_ratio=0.01,
        recovery_ratio=0.01,
        cooldown_ratio=0.0,
        halt_ratio=0.0,
        halt_count=0,
        incident_count=2,
        mttr_seconds=120.0,
        mtbf_seconds=40_000.0,
        reliability_score=98.0,
    )
    store = QualificationStore(tmp_path / "qualification.json")

    saved = store.save(
        result,
        qualification,
        reliability=reliability,
    )
    loaded = store.load()

    assert loaded == saved
    assert loaded is not None
    assert loaded.reliability_score == 98.0
    assert loaded.reliability_observation_seconds == 86_400.0
    assert loaded.normal_ratio == 0.97
    assert loaded.mttr_seconds == 120.0
    assert loaded.mtbf_seconds == 40_000.0

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from .chaos import ChaosScenario
from .runtime_factory import isolated_multiasset_runtime
from .soak import SoakResult, run_multiasset_soak
from .soak_gate import SoakQualification, evaluate_soak_qualification


@dataclass(frozen=True)
class QualificationCaseResult:
    name: str
    soak: SoakResult
    qualification: SoakQualification
    expected_safe_failure: bool


@dataclass(frozen=True)
class QualificationSuiteResult:
    passed: bool
    cases: tuple[QualificationCaseResult, ...]
    reasons: tuple[str, ...]


def _chaos_cases(symbol: str, step: int) -> tuple[tuple[str, tuple[ChaosScenario, ...]], ...]:
    return (
        ("baseline", ()),
        ("nan_last_close", (ChaosScenario("nan_last_close", step=step, symbol=symbol),)),
        ("duplicate_timestamp", (ChaosScenario("duplicate_timestamp", step=step, symbol=symbol),)),
        ("ohlc_violation", (ChaosScenario("ohlc_violation", step=step, symbol=symbol),)),
        ("stale_prices", (ChaosScenario("stale_prices", step=step, symbol=symbol),)),
    )


def run_qualification_suite(
    markets: dict[str, pd.DataFrame],
    *,
    workspace_root: str | Path = "artifacts/qualification_suite",
    max_cycles: int = 100,
) -> QualificationSuiteResult:
    if len(markets) < 2:
        raise ValueError("qualification suite requires at least two assets")

    workspace_root = Path(workspace_root)
    target_symbol = sorted(markets)[0]
    chaos_step = max(0, min(max_cycles - 1, max_cycles // 2))

    results: list[QualificationCaseResult] = []
    reasons: list[str] = []

    for name, chaos in _chaos_cases(target_symbol, chaos_step):
        runtime = isolated_multiasset_runtime(workspace_root / name)
        soak = run_multiasset_soak(
            runtime,
            markets,
            max_cycles=max_cycles,
            chaos=chaos,
        )
        qualification = evaluate_soak_qualification(soak)

        if name == "baseline":
            safe_failure = False
            if not qualification.passed:
                reasons.append("baseline qualification failed")
        else:
            safe_failure = (
                soak.governor_verdict != "TRADE"
                or soak.failures > 0
            )
            if not safe_failure:
                reasons.append(f"chaos case {name} was not detected")

        results.append(
            QualificationCaseResult(
                name=name,
                soak=soak,
                qualification=qualification,
                expected_safe_failure=safe_failure,
            )
        )

    baseline_ok = results[0].qualification.passed
    chaos_ok = all(case.expected_safe_failure for case in results[1:])

    return QualificationSuiteResult(
        passed=baseline_ok and chaos_ok,
        cases=tuple(results),
        reasons=tuple(reasons),
    )

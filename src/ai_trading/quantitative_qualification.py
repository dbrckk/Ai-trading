from __future__ import annotations

from dataclasses import dataclass

from .benchmark_gate import BenchmarkGateResult
from .bootstrap_gate import BootstrapGateResult
from .regime_gate import RegimeGateResult
from .sensitivity_gate import SensitivityGateResult
from .soak_gate import SoakQualification


@dataclass(frozen=True)
class QuantitativeQualification:
    qualified: bool
    passed_gates: int
    total_gates: int
    reasons: tuple[str, ...]


def evaluate_quantitative_qualification(
    *,
    benchmark: BenchmarkGateResult,
    regime: RegimeGateResult,
    bootstrap: BootstrapGateResult,
    sensitivity: SensitivityGateResult,
    soak: SoakQualification | None = None,
) -> QuantitativeQualification:
    gates = [
        ("benchmark", benchmark.passed, benchmark.reasons),
        ("regime", regime.passed, regime.reasons),
        ("bootstrap", bootstrap.passed, bootstrap.reasons),
        ("sensitivity", sensitivity.passed, sensitivity.reasons),
    ]
    if soak is not None:
        gates.append(("soak", soak.passed, soak.reasons))

    reasons: list[str] = []
    passed = 0
    for name, ok, gate_reasons in gates:
        if ok:
            passed += 1
            continue
        if gate_reasons:
            reasons.extend(f"{name}: {reason}" for reason in gate_reasons)
        else:
            reasons.append(f"{name}: failed")

    return QuantitativeQualification(
        qualified=passed == len(gates),
        passed_gates=passed,
        total_gates=len(gates),
        reasons=tuple(reasons),
    )

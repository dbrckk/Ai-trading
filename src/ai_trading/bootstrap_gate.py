from __future__ import annotations

from dataclasses import dataclass

from .bootstrap_robustness import BootstrapReport


@dataclass(frozen=True)
class BootstrapGatePolicy:
    min_probability_positive: float = 0.60
    max_probability_loss: float = 0.40
    min_lower_return: float = -0.15
    max_upper_drawdown: float = 0.30


@dataclass(frozen=True)
class BootstrapGateResult:
    passed: bool
    reasons: tuple[str, ...]


def evaluate_bootstrap_gate(
    report: BootstrapReport,
    policy: BootstrapGatePolicy | None = None,
) -> BootstrapGateResult:
    policy = policy or BootstrapGatePolicy()
    reasons: list[str] = []

    if report.probability_positive < policy.min_probability_positive:
        reasons.append("bootstrap positive-return probability below threshold")
    if report.probability_loss > policy.max_probability_loss:
        reasons.append("bootstrap loss probability above threshold")
    if report.lower_return < policy.min_lower_return:
        reasons.append("bootstrap lower-tail return below threshold")
    if report.upper_max_drawdown > policy.max_upper_drawdown:
        reasons.append("bootstrap drawdown tail above threshold")

    return BootstrapGateResult(passed=not reasons, reasons=tuple(reasons))

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from .chaos import ChaosScenario, apply_chaos
from .multiasset_runtime import MultiAssetPaperRuntime


@dataclass(frozen=True)
class SoakResult:
    cycles: int
    successes: int
    failures: int
    final_equity: float | None
    governor_verdict: str
    crisis_mode: str
    errors: tuple[str, ...]


def run_multiasset_soak(
    runtime: MultiAssetPaperRuntime,
    markets: dict[str, pd.DataFrame],
    *,
    start_bars: int = 100,
    max_cycles: int | None = None,
    chaos: tuple[ChaosScenario, ...] = (),
) -> SoakResult:
    if not markets:
        raise ValueError("markets cannot be empty")

    min_length = min(len(df) for df in markets.values())
    if min_length <= start_bars:
        raise ValueError("insufficient history for soak run")

    total_possible = min_length - start_bars
    cycles = total_possible if max_cycles is None else min(total_possible, max_cycles)

    successes = 0
    failures = 0
    errors: list[str] = []
    final_equity: float | None = None

    for offset in range(cycles):
        end = start_bars + offset + 1
        window = {
            symbol: df.iloc[:end].copy()
            for symbol, df in markets.items()
        }

        for scenario in chaos:
            window = apply_chaos(
                window,
                scenario,
                current_step=offset,
            )

        try:
            result = runtime.step(window)
            final_equity = result.equity
            successes += 1
        except Exception as exc:
            failures += 1
            errors.append(f"cycle={offset}: {type(exc).__name__}: {exc}")

    governor = runtime.governor_state_store.load()
    crisis = runtime.crisis_state_store.load()

    return SoakResult(
        cycles=cycles,
        successes=successes,
        failures=failures,
        final_equity=final_equity,
        governor_verdict=governor.verdict,
        crisis_mode=crisis.mode,
        errors=tuple(errors),
    )

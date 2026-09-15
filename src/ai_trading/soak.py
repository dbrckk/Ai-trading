from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

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
    max_drawdown: float = 0.0
    min_equity: float | None = None
    started_at_utc: str | None = None
    completed_at_utc: str | None = None
    duration_seconds: float = 0.0


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

    started_at = datetime.now(UTC)
    successes = 0
    failures = 0
    errors: list[str] = []
    final_equity: float | None = None
    peak_equity: float | None = None
    min_equity: float | None = None
    max_drawdown = 0.0

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
            peak_equity = (
                result.equity
                if peak_equity is None
                else max(peak_equity, result.equity)
            )
            min_equity = (
                result.equity
                if min_equity is None
                else min(min_equity, result.equity)
            )
            if peak_equity > 0:
                max_drawdown = max(
                    max_drawdown,
                    1.0 - result.equity / peak_equity,
                )
            successes += 1
        except (ValueError, RuntimeError, KeyError, IndexError, TypeError, OSError) as exc:
            failures += 1
            errors.append(f"cycle={offset}: {type(exc).__name__}: {exc}")

    governor = runtime.governor_state_store.load()
    crisis = runtime.crisis_state_store.load()

    completed_at = datetime.now(UTC)
    return SoakResult(
        cycles=cycles,
        successes=successes,
        failures=failures,
        final_equity=final_equity,
        governor_verdict=governor.verdict,
        crisis_mode=crisis.mode,
        errors=tuple(errors),
        max_drawdown=float(max_drawdown),
        min_equity=min_equity,
        started_at_utc=started_at.isoformat(),
        completed_at_utc=completed_at.isoformat(),
        duration_seconds=(completed_at - started_at).total_seconds(),
    )

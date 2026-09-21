from __future__ import annotations

import json
import os
from dataclasses import replace
from math import isfinite

from .config import RiskConfig

_ENV_NAME = "AI_TRADING_EXECUTION_COSTS_JSON"


def risk_config_for_symbol(
    symbol: str,
    base: RiskConfig | None = None,
    *,
    raw: str | None = None,
) -> RiskConfig:
    config = base or RiskConfig()
    payload_text = os.getenv(_ENV_NAME, "") if raw is None else raw
    payload_text = payload_text.strip()
    if not payload_text:
        return config

    try:
        payload = json.loads(payload_text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"{_ENV_NAME} must be valid JSON") from exc

    if not isinstance(payload, dict):
        raise ValueError(f"{_ENV_NAME} must contain a JSON object")

    override = payload.get(symbol)
    if override is None:
        return config
    if not isinstance(override, dict):
        raise ValueError(f"{_ENV_NAME}[{symbol!r}] must be a JSON object")

    allowed = {"transaction_cost_bps", "slippage_bps"}
    unknown = set(override).difference(allowed)
    if unknown:
        raise ValueError(
            f"{_ENV_NAME}[{symbol!r}] has unsupported keys: {sorted(unknown)}"
        )

    values: dict[str, float] = {}
    for name in allowed:
        if name not in override:
            continue
        try:
            value = float(override[name])
        except (TypeError, ValueError) as exc:
            raise ValueError(
                f"{_ENV_NAME}[{symbol!r}].{name} must be numeric"
            ) from exc
        if not isfinite(value) or value < 0:
            raise ValueError(
                f"{_ENV_NAME}[{symbol!r}].{name} must be finite and non-negative"
            )
        values[name] = value

    return replace(config, **values)

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CrisisAssetPolicy:
    disabled_cautious: tuple[str, ...] = ()
    disabled_defensive: tuple[str, ...] = ("crypto",)
    disabled_preservation: tuple[str, ...] = ("crypto", "energy")


def classify_symbol(symbol: str) -> str:
    upper = symbol.upper()
    if upper in {"GC=F", "SI=F", "HG=F", "PL=F", "PA=F"}:
        return "metals"
    if upper in {"CL=F", "BZ=F", "NG=F", "RB=F", "HO=F"}:
        return "energy"
    if upper.endswith("-USD") and any(
        token in upper for token in ("BTC", "ETH", "SOL", "XRP", "DOGE")
    ):
        return "crypto"
    if upper.endswith("=X"):
        return "fx"
    if upper.startswith("^"):
        return "equity_index"
    return "other"


def asset_allowed_in_mode(
    symbol: str,
    mode: str,
    policy: CrisisAssetPolicy | None = None,
) -> bool:
    policy = policy or CrisisAssetPolicy()
    asset_class = classify_symbol(symbol)

    if mode == "cautious":
        disabled = policy.disabled_cautious
    elif mode == "defensive":
        disabled = policy.disabled_defensive
    elif mode == "capital-preservation":
        disabled = policy.disabled_preservation
    else:
        disabled = ()

    return asset_class not in disabled

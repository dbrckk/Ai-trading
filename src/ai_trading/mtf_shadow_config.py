from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class ValidatedMTFShadowConfig:
    """Benchmark-validated, research-only MTF shadow configuration."""

    symbol: str
    config_name: str
    horizon_bars: int
    minimum_threshold: float
    atr_multiplier: float
    max_train_rows: int
    min_confidence: float
    min_train_rows: int = 500
    feature_warmup_rows: int = 600

    @property
    def horizon_minutes(self) -> int:
        return self.horizon_bars * 5

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


_VALIDATED_CONFIGS: dict[str, ValidatedMTFShadowConfig] = {
    "GC=F": ValidatedMTFShadowConfig(
        symbol="GC=F",
        config_name="h45m-min5bp-atr0.25-train1000-conf56",
        horizon_bars=9,
        minimum_threshold=0.0005,
        atr_multiplier=0.25,
        max_train_rows=1000,
        min_confidence=0.56,
    ),
    "^GDAXI": ValidatedMTFShadowConfig(
        symbol="^GDAXI",
        config_name="h45m-min5bp-atr0.25-train1000-conf60",
        horizon_bars=9,
        minimum_threshold=0.0005,
        atr_multiplier=0.25,
        max_train_rows=1000,
        min_confidence=0.60,
    ),
}


def validated_mtf_shadow_config(
    symbol: str,
) -> ValidatedMTFShadowConfig | None:
    """Return a benchmark-validated MTF config, or None when none passed."""

    return _VALIDATED_CONFIGS.get(symbol)

from __future__ import annotations

from pathlib import Path

from .allocation_state import AllocationStateStore
from .allocator_config_store import AllocatorConfigStore
from .audit import AuditLog
from .crisis_state_store import CrisisStateStore
from .economic_meta_store import EconomicMetaStore
from .expert_pool import ExpertPoolStore
from .governor_state_store import GovernorStateStore
from .meta_store import MetaRouterStore
from .multiasset_runtime import MultiAssetPaperRuntime
from .multiasset_state import MultiAssetStateStore
from .quality_store import QualityStore


def isolated_multiasset_runtime(root: str | Path) -> MultiAssetPaperRuntime:
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)

    return MultiAssetPaperRuntime(
        state_store=MultiAssetStateStore(root / "multiasset_state.json"),
        audit_log=AuditLog(root / "multiasset_audit.jsonl"),
        lock_path=str(root / "multiasset_runtime.lock"),
        model_root=root / "models" / "multiasset",
        batch_model_root=root / "models" / "multiasset_batch",
        quality_store=QualityStore(root / "model_quality.json"),
        meta_store=MetaRouterStore(root / "meta_router.json"),
        economic_meta_store=EconomicMetaStore(root / "economic_meta.json"),
        expert_pool_store=ExpertPoolStore(root / "expert_pool.json"),
        specialist_model_root=root / "models" / "specialists",
        allocation_state_store=AllocationStateStore(root / "global_allocation.json"),
        allocator_config_store=AllocatorConfigStore(root / "global_allocator_config.json"),
        crisis_state_store=CrisisStateStore(root / "crisis_state.json"),
        governor_state_store=GovernorStateStore(root / "risk_governor_state.json"),
    )

from __future__ import annotations

from .crisis_state_store import CrisisStateStore


def promotions_allowed(store: CrisisStateStore | None = None) -> bool:
    store = store or CrisisStateStore()
    return store.load().mode == "normal"

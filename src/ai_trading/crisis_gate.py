from __future__ import annotations

from .crisis_state_store import CrisisStateStore
from .governor_state_store import GovernorStateStore


def promotions_allowed(
    crisis_store: CrisisStateStore | None = None,
    governor_store: GovernorStateStore | None = None,
) -> bool:
    crisis_store = crisis_store or CrisisStateStore()
    governor_store = governor_store or GovernorStateStore()
    return (
        crisis_store.load().mode == "normal"
        and governor_store.load().verdict == "TRADE"
    )

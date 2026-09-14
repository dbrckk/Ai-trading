from pathlib import Path

from ai_trading.meta_router import MetaContext
from ai_trading.meta_store import MetaRouterStore


def test_meta_store_learns_context_specific_scores(tmp_path: Path) -> None:
    store = MetaRouterStore(tmp_path / "meta.json")
    context = MetaContext("GC=F", "bull_normal_vol", "normal", "low")

    for _ in range(8):
        store.update(context, "good", correct=True, edge=1.0)
    for _ in range(8):
        store.update(context, "bad", correct=False, edge=-1.0)

    scores = store.scores(context)
    assert scores["good"] > scores["bad"]

from ai_trading.evolution import MutationConfig, mutate_expert
from ai_trading.expert_factory import ExpertCandidate


def test_mutation_generates_distinct_variants() -> None:
    parent = ExpertCandidate(
        name="GC=F:trend:h3:t0.001",
        kind="trend",
        horizon_bars=3,
        return_threshold=0.001,
        compute_cost=1.0,
    )
    children = mutate_expert(
        parent,
        symbol="GC=F",
        config=MutationConfig(max_mutations_per_parent=4),
    )
    assert 1 <= len(children) <= 4
    assert len({c.name for c in children}) == len(children)
    assert all(c.name != parent.name for c in children)

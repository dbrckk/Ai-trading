from ai_trading.persistence import CommitOutcome, build_runtime_key


def test_build_runtime_key_is_stable() -> None:
    assert build_runtime_key("GC=F", "5m") == "paper:GC=F:5m:online-river:v1"


def test_commit_outcome_exposes_conflict() -> None:
    assert CommitOutcome.COMMITTED.value == "committed"
    assert CommitOutcome.CONFLICT.value == "conflict"

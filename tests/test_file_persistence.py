from ai_trading.model_codec import serialize_model
from ai_trading.online import RiverDirectionModel
from ai_trading.persistence import CommitOutcome, RuntimeStepCommit
from ai_trading.runtime_state import RuntimeState


def test_file_backend_survives_new_instance(tmp_path) -> None:
    from ai_trading.file_persistence import FilePaperPersistence

    backend = FilePaperPersistence(root=tmp_path)
    key = "paper:GC=F:5m:online-river:v1"
    loaded = backend.load_runtime(key, 100_000.0)
    assert loaded.is_new is True
    assert loaded.revision == 0

    outcome = backend.commit_step(
        key,
        RuntimeStepCommit(
            expected_revision=0,
            state=RuntimeState(
                cash=99_900.0,
                units=1.0,
                last_price=100.0,
                peak_equity=100_000.0,
                day_start_equity=100_000.0,
                last_processed="2026-09-15 10:00:00+00:00",
                processed_bars=1,
                last_learning_cycle_bar=0,
            ),
            model=serialize_model(RiverDirectionModel()),
            trade=None,
            audit_event="runtime_step",
            audit_payload={"processed_bars": 1},
        ),
    )

    assert outcome is CommitOutcome.COMMITTED
    restored = FilePaperPersistence(root=tmp_path).load_runtime(key, 100_000.0)
    assert restored.state.cash == 99_900.0
    assert restored.revision == 1
    assert restored.model is not None


def test_file_backend_rejects_stale_revision(tmp_path) -> None:
    from ai_trading.file_persistence import FilePaperPersistence

    backend = FilePaperPersistence(root=tmp_path)
    key = "paper:GC=F:5m:online-river:v1"
    backend.load_runtime(key, 100_000.0)
    commit = RuntimeStepCommit(
        expected_revision=1,
        state=RuntimeState(
            cash=100_000.0,
            units=0.0,
            last_price=100.0,
            peak_equity=100_000.0,
            day_start_equity=100_000.0,
            processed_bars=1,
        ),
        model=serialize_model(RiverDirectionModel()),
        trade=None,
        audit_event="runtime_step",
        audit_payload={},
    )

    assert backend.commit_step(key, commit) is CommitOutcome.CONFLICT


def test_file_backend_persists_unique_regimes(tmp_path) -> None:
    from ai_trading.file_persistence import FilePaperPersistence

    backend = FilePaperPersistence(root=tmp_path)
    key = "paper:GC=F:5m:online-river:v1"
    backend.load_runtime(key, 100_000.0)

    first = RuntimeStepCommit(
        expected_revision=0,
        state=RuntimeState(
            cash=99_900.0,
            units=1.0,
            last_price=100.0,
            peak_equity=100_000.0,
            day_start_equity=100_000.0,
            last_processed="2026-09-15 10:00:00+00:00",
            processed_bars=1,
        ),
        model=serialize_model(RiverDirectionModel()),
        trade=None,
        audit_event="runtime_step",
        audit_payload={},
        observed_regime="bull_normal_vol",
    )
    second = RuntimeStepCommit(
        expected_revision=1,
        state=RuntimeState(
            cash=99_800.0,
            units=1.0,
            last_price=100.0,
            peak_equity=100_000.0,
            day_start_equity=100_000.0,
            last_processed="2026-09-15 10:05:00+00:00",
            processed_bars=2,
        ),
        model=serialize_model(RiverDirectionModel()),
        trade=None,
        audit_event="runtime_step",
        audit_payload={},
        observed_regime="bull_normal_vol",
    )

    assert backend.commit_step(key, first) is CommitOutcome.COMMITTED
    assert backend.commit_step(key, second) is CommitOutcome.COMMITTED
    restored = FilePaperPersistence(root=tmp_path)
    assert restored.list_regimes(key) == ("bull_normal_vol",)
    assert restored.list_burnin_snapshots(key)[-1].regimes_covered == 1

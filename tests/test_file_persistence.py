from ai_trading.model_codec import serialize_model
from ai_trading.online import RiverDirectionModel
from ai_trading.persistence import CommitOutcome, RuntimeStepCommit, SchedulerDelivery
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



def test_file_backend_loads_shadow_quality_from_audit(tmp_path) -> None:
    from ai_trading.file_persistence import FilePaperPersistence

    backend = FilePaperPersistence(root=tmp_path)
    payloads = [
        {
            "prediction": {"side": 1, "confidence": 0.80},
            "shadow_challenger": {
                "prediction": {"side": 1, "confidence": 0.90},
                "realized_label": 1,
            },
        },
        {
            "prediction": {"side": 1, "confidence": 0.75},
            "shadow_challenger": {
                "prediction": {"side": 0, "confidence": 0.70},
                "realized_label": 0,
            },
        },
    ]
    for payload in payloads:
        backend.audit_log.append("runtime_step", payload)

    comparison = backend.load_shadow_quality("paper:GC=F:5m:online-river:v1")

    assert comparison.observations == 2
    assert comparison.river.observations == 2
    assert comparison.challenger.observations == 2


def test_file_backend_persists_scheduler_deliveries(tmp_path) -> None:
    from ai_trading.file_persistence import FilePaperPersistence

    backend = FilePaperPersistence(root=tmp_path)
    delivery = SchedulerDelivery(
        timestamp_utc="2026-09-21T16:00:00+00:00",
        source="cloudflare",
        status_code=200,
        ok=True,
        processed=2,
    )
    backend.record_scheduler_delivery(delivery)

    restored = FilePaperPersistence(root=tmp_path)
    assert restored.list_scheduler_deliveries() == (delivery,)



def test_file_backend_isolates_runtime_keys(tmp_path) -> None:
    from ai_trading.file_persistence import FilePaperPersistence

    backend = FilePaperPersistence(root=tmp_path)
    gold_key = "paper:GC=F:5m:online-river:v1"
    dax_key = "paper:^GDAXI:5m:online-river:v1"

    gold = backend.load_runtime(gold_key, 100_000.0)
    dax = backend.load_runtime(dax_key, 100_000.0)
    assert gold.is_new is True
    assert dax.is_new is True

    gold_commit = RuntimeStepCommit(
        expected_revision=0,
        state=RuntimeState(
            cash=101_000.0,
            units=0.0,
            last_price=100.0,
            peak_equity=101_000.0,
            day_start_equity=100_000.0,
            processed_bars=1,
        ),
        model=serialize_model(RiverDirectionModel()),
        trade=None,
        audit_event="runtime_step",
        audit_payload={"market": "gold"},
        observed_regime="gold_regime",
    )
    dax_commit = RuntimeStepCommit(
        expected_revision=0,
        state=RuntimeState(
            cash=99_000.0,
            units=0.0,
            last_price=200.0,
            peak_equity=100_000.0,
            day_start_equity=100_000.0,
            processed_bars=1,
        ),
        model=serialize_model(RiverDirectionModel()),
        trade=None,
        audit_event="runtime_step",
        audit_payload={"market": "dax"},
        observed_regime="dax_regime",
    )

    assert backend.commit_step(gold_key, gold_commit) is CommitOutcome.COMMITTED
    assert backend.commit_step(dax_key, dax_commit) is CommitOutcome.COMMITTED

    restored = FilePaperPersistence(root=tmp_path)
    gold_restored = restored.load_runtime(gold_key, 100_000.0)
    dax_restored = restored.load_runtime(dax_key, 100_000.0)

    assert gold_restored.state.cash == 101_000.0
    assert dax_restored.state.cash == 99_000.0
    assert restored.list_regimes(gold_key) == ("gold_regime",)
    assert restored.list_regimes(dax_key) == ("dax_regime",)
    assert restored.state_store.path == tmp_path / "runtime_state.json"
    assert restored._state_store_for(dax_key).path != restored.state_store.path
    assert restored._model_path_for(dax_key) != restored.model_path

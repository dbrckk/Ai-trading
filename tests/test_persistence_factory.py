from ai_trading.file_persistence import FilePaperPersistence


def test_factory_uses_file_backend_without_database_url(monkeypatch, tmp_path) -> None:
    from ai_trading.persistence_factory import build_paper_persistence

    monkeypatch.delenv("AI_TRADING_DATABASE_URL", raising=False)
    persistence = build_paper_persistence(file_root=tmp_path)
    assert isinstance(persistence, FilePaperPersistence)


def test_factory_treats_blank_database_url_as_absent(monkeypatch, tmp_path) -> None:
    from ai_trading.persistence_factory import build_paper_persistence

    monkeypatch.setenv("AI_TRADING_DATABASE_URL", "   ")
    persistence = build_paper_persistence(file_root=tmp_path)
    assert isinstance(persistence, FilePaperPersistence)


def test_factory_uses_postgres_and_initializes_schema(monkeypatch) -> None:
    import ai_trading.persistence_factory as factory

    monkeypatch.setenv("AI_TRADING_DATABASE_URL", "postgresql://example.invalid/db")

    calls: list[str] = []

    def fake_initialize(self) -> None:
        calls.append(self.database_url)

    monkeypatch.setattr(factory.PostgresPaperPersistence, "initialize_schema", fake_initialize)
    persistence = factory.build_paper_persistence()

    assert isinstance(persistence, factory.PostgresPaperPersistence)
    assert calls == ["postgresql://example.invalid/db"]

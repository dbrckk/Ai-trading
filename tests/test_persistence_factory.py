def test_factory_uses_file_backend_without_database_url(monkeypatch, tmp_path) -> None:
    from ai_trading.file_persistence import FilePaperPersistence
    from ai_trading.persistence_factory import build_paper_persistence

    monkeypatch.delenv("AI_TRADING_DATABASE_URL", raising=False)
    persistence = build_paper_persistence(file_root=tmp_path)
    assert isinstance(persistence, FilePaperPersistence)


def test_factory_uses_postgres_and_initializes_schema(monkeypatch) -> None:
    from ai_trading.persistence_factory import build_paper_persistence
    from ai_trading.postgres_persistence import PostgresPaperPersistence

    monkeypatch.setenv("AI_TRADING_DATABASE_URL", "postgresql://example.invalid/db")

    calls: list[str] = []

    def fake_initialize(self) -> None:
        calls.append(self.database_url)

    monkeypatch.setattr(PostgresPaperPersistence, "initialize_schema", fake_initialize)
    persistence = build_paper_persistence()

    assert isinstance(persistence, PostgresPaperPersistence)
    assert calls == ["postgresql://example.invalid/db"]

from __future__ import annotations

import os
from pathlib import Path

from .file_persistence import FilePaperPersistence
from .persistence import PaperPersistence
from .postgres_persistence import PostgresPaperPersistence


def build_paper_persistence(
    *,
    file_root: str | Path = "artifacts",
) -> PaperPersistence:
    database_url = os.environ.get("AI_TRADING_DATABASE_URL")
    if not database_url:
        return FilePaperPersistence(root=file_root)

    persistence = PostgresPaperPersistence(database_url)
    persistence.initialize_schema()
    return persistence

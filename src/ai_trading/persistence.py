from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import joblib


@dataclass(frozen=True)
class ModelArtifact:
    path: Path
    metadata: dict[str, Any]


class ModelStore:
    def __init__(self, root: str | Path = "artifacts/models") -> None:
        self.root = Path(root)

    def save(self, name: str, model: object, metadata: dict[str, Any] | None = None) -> ModelArtifact:
        self.root.mkdir(parents=True, exist_ok=True)
        path = self.root / f"{name}.joblib"
        payload = {"model": model, "metadata": metadata or {}}
        joblib.dump(payload, path)
        return ModelArtifact(path=path, metadata=payload["metadata"])

    def load(self, name: str) -> ModelArtifact:
        path = self.root / f"{name}.joblib"
        if not path.exists():
            raise FileNotFoundError(path)
        payload = joblib.load(path)
        return ModelArtifact(path=path, metadata=dict(payload.get("metadata", {})))

    def load_model(self, name: str) -> object:
        path = self.root / f"{name}.joblib"
        if not path.exists():
            raise FileNotFoundError(path)
        payload = joblib.load(path)
        return payload["model"]

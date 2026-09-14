from __future__ import annotations

import json
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
        self.pointer_path = self.root / "active.json"

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

    def activate(self, name: str) -> ModelArtifact:
        artifact = self.load(name)
        self.root.mkdir(parents=True, exist_ok=True)
        temp = self.pointer_path.with_suffix(".tmp")
        temp.write_text(json.dumps({"active": name}, sort_keys=True), encoding="utf-8")
        temp.replace(self.pointer_path)
        return artifact

    def active_name(self) -> str | None:
        if not self.pointer_path.exists():
            return None
        payload = json.loads(self.pointer_path.read_text(encoding="utf-8"))
        value = payload.get("active")
        return str(value) if value else None

    def load_active_model(self) -> object:
        name = self.active_name()
        if name is None:
            raise RuntimeError("No active model")
        return self.load_model(name)

from __future__ import annotations

import hashlib
import json
import re
import shutil
from dataclasses import asdict
from pathlib import Path

import joblib

from .multiasset_state import AssetPosition, MultiAssetState


class MultiAssetCheckpointStore:
    """Checkpoint portfolio state and online models as one durable generation."""

    def __init__(self, root: str | Path, *, retain_generations: int = 3) -> None:
        if retain_generations < 1:
            raise ValueError("retain_generations must be at least 1")
        self.root = Path(root)
        self.current_path = self.root / "CURRENT"
        self.retain_generations = retain_generations

    def _generation_dir(self, generation: str) -> Path:
        return self.root / self._validate_generation(generation)

    @staticmethod
    def _validate_generation(generation: str) -> str:
        if re.fullmatch(r"step-\d{12}", generation) is None:
            raise ValueError("invalid multiasset checkpoint generation")
        return generation

    @staticmethod
    def _model_filename(symbol: str) -> str:
        digest = hashlib.sha256(symbol.encode("utf-8")).hexdigest()[:16]
        return f"model-{digest}.joblib"

    @staticmethod
    def _sha256(path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()

    def commit(
        self,
        state: MultiAssetState,
        models: dict[str, object],
    ) -> str:
        generation = self._validate_generation(f"step-{state.processed_bars:012d}")
        final_dir = self._generation_dir(generation)
        temp_dir = self.root / f".{generation}.tmp"
        self.root.mkdir(parents=True, exist_ok=True)
        if temp_dir.exists():
            shutil.rmtree(temp_dir)
        temp_dir.mkdir()

        state_path = temp_dir / "state.json"
        state_payload = json.dumps(asdict(state), sort_keys=True)
        state_path.write_text(state_payload, encoding="utf-8")
        model_files: dict[str, str] = {}
        for symbol, model in sorted(models.items()):
            filename = self._model_filename(symbol)
            joblib.dump(model, temp_dir / filename)
            model_files[symbol] = filename

        manifest = {
            "generation": generation,
            "processed_bars": state.processed_bars,
            "last_processed": state.last_processed,
            "state": {"file": "state.json", "sha256": self._sha256(state_path)},
            "models": {
                symbol: {
                    "file": filename,
                    "sha256": self._sha256(temp_dir / filename),
                }
                for symbol, filename in model_files.items()
            },
        }
        manifest_path = temp_dir / "manifest.json"
        manifest_path.write_text(
            json.dumps(manifest, sort_keys=True),
            encoding="utf-8",
        )
        if final_dir.exists():
            shutil.rmtree(temp_dir)
            raise ValueError(f"multiasset checkpoint already exists: {generation}")
        temp_dir.replace(final_dir)

        self._publish_current(generation)
        self._prune_old_generations(current=generation)
        return generation

    def _publish_current(self, generation: str) -> None:
        pointer_tmp = self.current_path.with_suffix(".tmp")
        pointer_tmp.write_text(generation, encoding="utf-8")
        pointer_tmp.replace(self.current_path)

    def _prune_old_generations(self, *, current: str) -> None:
        generations = sorted(
            path
            for path in self.root.glob("step-*")
            if path.is_dir() and path.name != current
        )
        removable = max(0, len(generations) - (self.retain_generations - 1))
        for path in generations[:removable]:
            shutil.rmtree(path)

    def _load_generation(
        self,
        generation: str,
    ) -> tuple[MultiAssetState, dict[str, object]]:
        directory = self._generation_dir(generation)
        manifest_path = directory / "manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if manifest.get("generation") != generation:
            raise ValueError("multiasset checkpoint generation mismatch")

        state_meta = manifest["state"]
        state_path = directory / state_meta["file"]
        if self._sha256(state_path) != state_meta["sha256"]:
            raise ValueError("multiasset checkpoint state checksum mismatch")
        payload = json.loads(state_path.read_text(encoding="utf-8"))
        payload["positions"] = {
            symbol: AssetPosition(**position)
            for symbol, position in payload.get("positions", {}).items()
        }
        state = MultiAssetState(**payload)

        models: dict[str, object] = {}
        for symbol, metadata in manifest.get("models", {}).items():
            path = directory / metadata["file"]
            if self._sha256(path) != metadata["sha256"]:
                raise ValueError(
                    f"multiasset checkpoint model checksum mismatch: {symbol}"
                )
            models[symbol] = joblib.load(path)
        return state, models

    def _newer_valid_generation(self, current: str | None) -> str | None:
        candidates = sorted(
            path.name
            for path in self.root.glob("step-*")
            if path.is_dir() and (current is None or path.name > current)
        )
        for generation in reversed(candidates):
            try:
                self._load_generation(generation)
            except (FileNotFoundError, KeyError, ValueError, json.JSONDecodeError):
                continue
            return generation
        return None

    def load(self) -> tuple[MultiAssetState, dict[str, object]] | None:
        current: str | None = None
        if self.current_path.exists():
            current = self.current_path.read_text(encoding="utf-8").strip()
            if not current:
                raise ValueError("multiasset checkpoint pointer is empty")
            current = self._validate_generation(current)
            loaded = self._load_generation(current)
        else:
            loaded = None

        recovered = self._newer_valid_generation(current)
        if recovered is not None:
            self._publish_current(recovered)
            self._prune_old_generations(current=recovered)
            return self._load_generation(recovered)

        return loaded

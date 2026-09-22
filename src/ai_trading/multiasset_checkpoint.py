from __future__ import annotations

import hashlib
import json
import shutil
from dataclasses import asdict
from pathlib import Path

import joblib

from .multiasset_state import AssetPosition, MultiAssetState


class MultiAssetCheckpointStore:
    """Checkpoint portfolio state and online models as one durable generation."""

    def __init__(self, root: str | Path) -> None:
        self.root = Path(root)
        self.current_path = self.root / "CURRENT"

    def _generation_dir(self, generation: str) -> Path:
        return self.root / generation

    @staticmethod
    def _safe_symbol(symbol: str) -> str:
        return symbol.replace("/", "_").replace("=", "_").replace("^", "_")

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
        generation = f"step-{state.processed_bars:012d}"
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
            filename = f"{self._safe_symbol(symbol)}.joblib"
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
            shutil.rmtree(final_dir)
        temp_dir.replace(final_dir)

        pointer_tmp = self.current_path.with_suffix(".tmp")
        pointer_tmp.write_text(generation, encoding="utf-8")
        pointer_tmp.replace(self.current_path)
        return generation

    def load(self) -> tuple[MultiAssetState, dict[str, object]] | None:
        if not self.current_path.exists():
            return None
        generation = self.current_path.read_text(encoding="utf-8").strip()
        if not generation:
            raise ValueError("multiasset checkpoint pointer is empty")
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
